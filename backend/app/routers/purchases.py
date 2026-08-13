from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Attachment, BusinessOrder, Employee, InventoryMovement, Product, ProductVariant, PurchaseOrder, PurchaseOrderItem, User
from ..permissions import employee_for_user
from ..schemas import PurchaseOrderCreate, PurchaseOrderItemRead, PurchaseOrderRead, PurchaseOrderUpdate


router = APIRouter(prefix="/api/v1/purchases", tags=["purchases"])


def get_order(order_id: int, db: Session) -> PurchaseOrder:
    order = db.get(PurchaseOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="采购单不存在")
    return order


def default_purchaser(db: Session, user: User | None = None) -> str:
    employee = db.scalar(
        select(Employee)
        .where(
            Employee.status != "离职",
            or_(
                Employee.position.like("%采购%"),
                Employee.department.like("%采购%"),
                Employee.name.like("%采购%"),
                Employee.responsibility.like("%采购%"),
            ),
        )
        .order_by(Employee.id)
    )
    if employee:
        return employee.name
    return (user.display_name or user.username) if user else ""


def serialize_order(order: PurchaseOrder, db: Session) -> PurchaseOrderRead:
    items = db.scalars(select(PurchaseOrderItem).where(PurchaseOrderItem.order_id == order.id).order_by(PurchaseOrderItem.id)).all()
    data = PurchaseOrderRead.model_validate(order)
    data.items = [PurchaseOrderItemRead.model_validate(item) for item in items]
    result = data.model_dump()
    source_no = linked_order_no(order.order_no)
    business = db.scalar(select(BusinessOrder).where(BusinessOrder.order_no == source_no)) if source_no else None
    result.update(
        {
            "source_type": "订单生成" if business else "采购新增",
            "source_no": source_no,
            "source_text": f"订单生成：{source_no}" if business else "采购新增",
            "requester": business.requester if business else order.purchaser,
            "created_by": business.requester if business else order.purchaser,
        }
    )
    return result


def linked_order_no(purchase_no: str) -> str:
    return purchase_no[3:] if str(purchase_no or "").startswith("CG-") else ""


def linked_business_order(order: PurchaseOrder, db: Session) -> BusinessOrder | None:
    source = linked_order_no(order.order_no)
    if not source:
        return None
    return db.scalar(select(BusinessOrder).where(BusinessOrder.order_no == source))


def sync_business_order_from_purchase(order: PurchaseOrder, db: Session):
    business = linked_business_order(order, db)
    if not business or business.status in {"已完成", "已取消", "已驳回"}:
        return
    if "已入库" in order.status:
        business.status = "待配送" if business.need_delivery else "已完成"
    elif "待入库" in order.status:
        business.status = "待入库"
    elif "待采购" in order.status:
        business.status = "待采购"


def attach_purchase_receipts(order: PurchaseOrder, payload: dict | None, db: Session, user: User):
    if not payload:
        return
    receipts = payload.get("receipts") or payload.get("attachments") or []
    if not isinstance(receipts, list):
        return
    for entry in receipts:
        if not isinstance(entry, dict):
            continue
        data_url = str(entry.get("data_url") or "")
        file_name = str(entry.get("file_name") or entry.get("name") or "采购收据")
        if not data_url:
            continue
        db.add(
            Attachment(
                target_type="采购单",
                target_id=order.id,
                target_name=order.order_no,
                file_name=file_name,
                file_type=str(entry.get("file_type") or entry.get("type") or "image/*"),
                file_size=int(entry.get("file_size") or entry.get("size") or 0),
                data_url=data_url,
                notes=str(entry.get("notes") or "采购完成上传收据"),
                uploader_id=user.id,
                uploader_name=user.display_name or user.username,
            )
        )


def attach_purchase_details(order: PurchaseOrder, payload: dict | None, db: Session, user: User):
    if not payload:
        return
    details = payload.get("product_details") or payload.get("details") or []
    if not isinstance(details, list):
        return
    for entry in details:
        if not isinstance(entry, dict):
            continue
        data_url = str(entry.get("data_url") or "")
        if not data_url:
            continue
        db.add(
            Attachment(
                target_type="采购单",
                target_id=order.id,
                target_name=order.order_no,
                file_name=str(entry.get("file_name") or entry.get("name") or "商品详情"),
                file_type=str(entry.get("file_type") or entry.get("type") or "image/*"),
                file_size=int(entry.get("file_size") or entry.get("size") or 0),
                data_url=data_url,
                notes=str(entry.get("notes") or "商品详情"),
                uploader_id=user.id,
                uploader_name=user.display_name or user.username,
            )
        )


def normalize_item_names(item: PurchaseOrderItem, db: Session):
    product = db.get(Product, item.product_id)
    if not product:
        raise HTTPException(status_code=400, detail="采购明细商品不存在")
    item.product_name = item.product_name or product.name
    if item.variant_id:
        variant = db.get(ProductVariant, item.variant_id)
        if not variant or variant.product_id != product.id:
            raise HTTPException(status_code=400, detail="采购明细规格不存在")
        item.variant_name = item.variant_name or variant.specification or variant.code
        item.unit = item.unit or variant.unit
    else:
        item.unit = item.unit or product.purchase_unit or product.unit


def bundle_complete_stock(product: Product, db: Session) -> float:
    variants = db.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id)).all()
    enabled_variants = [variant for variant in variants if (variant.conversion_quantity or 0) > 0]
    if not enabled_variants:
        return float(product.stock or 0)
    return float(min(float(variant.stock or 0) / float(variant.conversion_quantity or 1) for variant in enabled_variants))


def receive_bundle_item(order: PurchaseOrder, item: PurchaseOrderItem, product: Product, db: Session):
    received_quantity = float(item.received_quantity or item.quantity or 0)
    variants = db.scalars(
        select(ProductVariant)
        .where(ProductVariant.product_id == product.id)
        .order_by(ProductVariant.sort_order, ProductVariant.id)
    ).all()
    if not variants:
        raise HTTPException(status_code=400, detail=f"{product.name} 已开启成套采购，但没有设置大/中/小型号")
    before_bundle_stock = bundle_complete_stock(product, db)
    product.reference_purchase_price = item.unit_price
    triggered_variant_name = item.variant_name
    for variant in variants:
        before_stock = float(variant.stock or 0)
        add_quantity = received_quantity * float(variant.conversion_quantity or 1)
        variant.stock = before_stock + add_quantity
        after_stock = float(variant.stock or 0)
        db.add(
            InventoryMovement(
                product_id=product.id,
                variant_id=variant.id,
                product_name=item.product_name or product.name,
                variant_name=variant.specification or variant.code,
                movement_type="成套拆分入库",
                direction="入库",
                quantity=add_quantity,
                before_stock=before_stock,
                after_stock=after_stock,
                unit=variant.unit or product.unit,
                unit_price=variant.reference_purchase_price,
                total_amount=add_quantity * float(variant.reference_purchase_price or 0),
                source_type="采购单",
                source_no=order.order_no,
                operator=order.purchaser,
                notes=f"整套入库 {received_quantity:g}{product.purchase_unit or product.unit} 自动拆分；{item.notes or ''}".strip(),
            )
        )
    product.stock = int(bundle_complete_stock(product, db))
    db.add(
        InventoryMovement(
            product_id=product.id,
            variant_id=None,
            product_name=item.product_name or product.name,
            variant_name="成套采购",
            movement_type="成套采购入库",
            direction="入库",
            quantity=received_quantity,
            before_stock=before_bundle_stock,
            after_stock=float(product.stock or 0),
            unit=product.purchase_unit or product.unit,
            unit_price=item.unit_price,
            total_amount=received_quantity * item.unit_price,
            source_type="采购单",
            source_no=order.order_no,
            operator=order.purchaser,
            notes=(f"由型号 {triggered_variant_name} 触发整套采购；" if triggered_variant_name else "") + (item.notes or ""),
        )
    )


@router.get("")
def list_orders(
    keyword: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    filters = []
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(PurchaseOrder.order_no.like(pattern), PurchaseOrder.supplier.like(pattern), PurchaseOrder.purchaser.like(pattern)))
    orders = db.scalars(select(PurchaseOrder).where(*filters).order_by(PurchaseOrder.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(PurchaseOrder).where(*filters)) or 0
    return {"items": [serialize_order(order, db) for order in orders], "total": total}


@router.get("/my")
def list_my_orders(
    keyword: str = Query(default="", max_length=100),
    include_done: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    employee = employee_for_user(user, db)
    names = {user.display_name, user.username}
    if employee:
        names.add(employee.name)
    names = {name for name in names if name}
    if not names:
        return {"items": [], "total": 0}
    filters = [PurchaseOrder.purchaser.in_(names)]
    if not include_done:
        filters.append(PurchaseOrder.status != "已入库")
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(PurchaseOrder.order_no.like(pattern), PurchaseOrder.supplier.like(pattern), PurchaseOrder.purchaser.like(pattern)))
    orders = db.scalars(select(PurchaseOrder).where(*filters).order_by(PurchaseOrder.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(PurchaseOrder).where(*filters)) or 0
    return {"items": [serialize_order(order, db) for order in orders], "total": total}


@router.get("/inbound")
def list_inbound_orders(
    keyword: str = Query(default="", max_length=100),
    include_done: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    filters = []
    if include_done:
        filters.append(PurchaseOrder.status.in_(["待入库", "已入库"]))
    else:
        filters.append(PurchaseOrder.status == "待入库")
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(PurchaseOrder.order_no.like(pattern), PurchaseOrder.supplier.like(pattern), PurchaseOrder.purchaser.like(pattern)))
    orders = db.scalars(select(PurchaseOrder).where(*filters).order_by(PurchaseOrder.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(PurchaseOrder).where(*filters)) or 0
    return {"items": [serialize_order(order, db) for order in orders], "total": total}


@router.post("", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if db.scalar(select(PurchaseOrder).where(PurchaseOrder.order_no == payload.order_no)):
        raise HTTPException(status_code=409, detail="采购单号已存在")
    values = payload.model_dump(exclude={"items"})
    values["purchaser"] = values.get("purchaser") or default_purchaser(db, user)
    if "status" not in payload.model_fields_set:
        values["status"] = "待采购"
    order = PurchaseOrder(**values)
    db.add(order)
    db.flush()
    for item_payload in payload.items:
        item = PurchaseOrderItem(order_id=order.id, **item_payload.model_dump())
        normalize_item_names(item, db)
        db.add(item)
    db.commit()
    db.refresh(order)
    return serialize_order(order, db)


@router.post("/{order_id}/assign", response_model=PurchaseOrderRead)
def assign_order(
    order_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    order = get_order(order_id, db)
    if order.status == "已入库":
        raise HTTPException(status_code=400, detail="已入库采购单不能重新分配")
    purchaser = str(payload.get("purchaser") or "").strip()
    if not purchaser:
        raise HTTPException(status_code=400, detail="请填写采购员")
    order.purchaser = purchaser
    order.status = "待采购"
    db.commit()
    db.refresh(order)
    return serialize_order(order, db)


@router.post("/{order_id}/mark-purchased", response_model=PurchaseOrderRead)
def mark_purchased(
    order_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    order = get_order(order_id, db)
    if order.status == "已入库":
        raise HTTPException(status_code=400, detail="已入库采购单不能修改采购完成状态")
    if not order.purchaser:
        order.purchaser = default_purchaser(db, user)
    if order.status == "待分配":
        order.status = "待采购"
    if payload:
        if "supplier" in payload:
            order.supplier = str(payload.get("supplier") or "")
        if "freight_fee" in payload:
            order.freight_fee = float(payload.get("freight_fee") or 0)
        if "hll_fee" in payload:
            order.hll_fee = float(payload.get("hll_fee") or 0)
        if "notes" in payload:
            order.notes = str(payload.get("notes") or "")
        attach_purchase_receipts(order, payload, db, user)
        attach_purchase_details(order, payload, db, user)
        if isinstance(payload.get("items"), list):
            item_map = {int(entry.get("id") or 0): entry for entry in payload.get("items") if isinstance(entry, dict)}
            for item in db.scalars(select(PurchaseOrderItem).where(PurchaseOrderItem.order_id == order_id)).all():
                entry = item_map.get(item.id)
                if not entry:
                    continue
                item.quantity = float(entry.get("quantity") or item.quantity or 0)
                item.received_quantity = float(entry.get("received_quantity") or item.received_quantity or 0)
                item.unit = str(entry.get("unit") or item.unit or "")
                item.unit_price = float(entry.get("unit_price") or 0)
                item.notes = str(entry.get("notes") or item.notes or "")
    items = db.scalars(select(PurchaseOrderItem).where(PurchaseOrderItem.order_id == order_id)).all()
    if not items:
        raise HTTPException(status_code=400, detail="采购单没有明细")
    if any(float(item.unit_price or 0) <= 0 for item in items):
        raise HTTPException(status_code=400, detail="请先填写实际采购单价")
    order.status = "待入库"
    sync_business_order_from_purchase(order, db)
    db.commit()
    db.refresh(order)
    return serialize_order(order, db)


@router.put("/{order_id}", response_model=PurchaseOrderRead)
def update_order(
    order_id: int,
    payload: PurchaseOrderUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    order = get_order(order_id, db)
    if order.status == "已入库":
        raise HTTPException(status_code=400, detail="已入库采购单不能修改")
    values = payload.model_dump(exclude_unset=True, exclude={"items"})
    if "order_no" in values and db.scalar(select(PurchaseOrder).where(PurchaseOrder.order_no == values["order_no"], PurchaseOrder.id != order_id)):
        raise HTTPException(status_code=409, detail="采购单号已存在")
    for key, value in values.items():
        setattr(order, key, value)
    if "purchaser" in values and order.purchaser and order.status == "待分配":
        order.status = "待采购"
    if payload.items is not None:
        for item in db.scalars(select(PurchaseOrderItem).where(PurchaseOrderItem.order_id == order_id)).all():
            db.delete(item)
        db.flush()
        for item_payload in payload.items:
            item = PurchaseOrderItem(order_id=order.id, **item_payload.model_dump())
            normalize_item_names(item, db)
            db.add(item)
    db.commit()
    db.refresh(order)
    return serialize_order(order, db)


@router.post("/{order_id}/receive", response_model=PurchaseOrderRead)
def receive_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    order = get_order(order_id, db)
    if order.status == "已入库":
        raise HTTPException(status_code=400, detail="采购单已入库")
    if order.status == "待分配":
        order.purchaser = order.purchaser or default_purchaser(db, user)
        order.status = "待采购"
    if order.status == "待采购":
        raise HTTPException(status_code=400, detail="请先填写实际采购价并标记采购完成")
    items = db.scalars(select(PurchaseOrderItem).where(PurchaseOrderItem.order_id == order_id)).all()
    if not items:
        raise HTTPException(status_code=400, detail="采购单没有明细")
    for item in items:
        received_quantity = item.received_quantity or item.quantity
        item.received_quantity = received_quantity
        product = db.get(Product, item.product_id)
        if not product:
            raise HTTPException(status_code=400, detail="采购明细商品不存在")
        if product.package_conversion_enabled:
            receive_bundle_item(order, item, product, db)
            continue
        if item.variant_id:
            variant = db.get(ProductVariant, item.variant_id)
            if not variant:
                raise HTTPException(status_code=400, detail="采购明细规格不存在")
            before_stock = float(variant.stock or 0)
            variant.stock = float(variant.stock or 0) + received_quantity
            variant.reference_purchase_price = item.unit_price
            if not product.package_conversion_enabled:
                product.stock = int(sum(v.stock or 0 for v in db.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id)).all()))
            product.reference_purchase_price = item.unit_price
            after_stock = float(variant.stock or 0)
            unit = variant.unit or item.unit
            variant_name = item.variant_name or variant.specification or variant.code
        else:
            before_stock = float(product.stock or 0)
            product.stock = int((product.stock or 0) + received_quantity)
            product.reference_purchase_price = item.unit_price
            after_stock = float(product.stock or 0)
            unit = item.unit or product.purchase_unit or product.unit
            variant_name = ""
        db.add(
            InventoryMovement(
                product_id=product.id,
                variant_id=item.variant_id,
                product_name=item.product_name or product.name,
                variant_name=variant_name,
                movement_type="采购入库",
                direction="入库",
                quantity=received_quantity,
                before_stock=before_stock,
                after_stock=after_stock,
                unit=unit,
                unit_price=item.unit_price,
                total_amount=received_quantity * item.unit_price,
                source_type="采购单",
                source_no=order.order_no,
                operator=order.purchaser,
                notes=item.notes,
            )
        )
    order.status = "已入库"
    sync_business_order_from_purchase(order, db)
    db.commit()
    db.refresh(order)
    return serialize_order(order, db)
