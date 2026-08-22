from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import BusinessOrder, InventoryMovement, OutboundOrder, OutboundOrderItem, Product, ProductVariant, Project, PurchaseReceipt, PurchaseReceiptAllocation, PurchaseReceiptItem, User


router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


def linked_business_order(outbound: OutboundOrder, db: Session) -> BusinessOrder | None:
    order_no = outbound.order_no[3:] if str(outbound.order_no or "").startswith("CK-") else ""
    if not order_no:
        return None
    return db.scalar(select(BusinessOrder).where(BusinessOrder.order_no == order_no))


def sync_business_order_from_outbound(outbound: OutboundOrder, db: Session):
    order = linked_business_order(outbound, db)
    if not order or order.status in {"已完成", "已取消", "已驳回"}:
        return
    if "已出库" in outbound.status:
        order.status = "待配送" if order.need_delivery else "已完成"


def variant_label(variant: ProductVariant) -> str:
    return variant.specification or variant.code


def product_stock(product: Product, db: Session) -> float:
    if product.package_conversion_enabled:
        variants = db.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id)).all()
        enabled_variants = [variant for variant in variants if (variant.conversion_quantity or 0) > 0]
        if enabled_variants:
            return float(min(float(variant.stock or 0) / float(variant.conversion_quantity or 1) for variant in enabled_variants))
        return float(product.stock or 0)
    variants = db.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id)).all()
    if variants:
        return float(sum(variant.stock or 0 for variant in variants))
    return float(product.stock or 0)


def serialize_movement(row: InventoryMovement):
    return {
        "id": row.id,
        "product_id": row.product_id,
        "variant_id": row.variant_id,
        "product_name": row.product_name,
        "variant_name": row.variant_name,
        "movement_type": row.movement_type,
        "direction": row.direction,
        "quantity": float(row.quantity or 0),
        "before_stock": float(row.before_stock or 0),
        "after_stock": float(row.after_stock or 0),
        "unit": row.unit,
        "unit_price": float(row.unit_price or 0),
        "total_amount": float(row.total_amount or 0),
        "source_type": row.source_type,
        "source_no": row.source_no,
        "operator": row.operator,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


def serialize_outbound(order: OutboundOrder, db: Session):
    items = db.scalars(select(OutboundOrderItem).where(OutboundOrderItem.order_id == order.id).order_by(OutboundOrderItem.id)).all()
    return {
        "id": order.id,
        "order_no": order.order_no,
        "outbound_type": order.outbound_type,
        "project_name": order.project_name,
        "handler": order.handler,
        "outbound_date": order.outbound_date.isoformat() if order.outbound_date else None,
        "status": order.status,
        "notes": order.notes,
        "created_at": order.created_at.isoformat() if order.created_at else "",
        "items": [
            {
                "id": item.id,
                "order_id": item.order_id,
                "product_id": item.product_id,
                "variant_id": item.variant_id,
                "product_name": item.product_name,
                "variant_name": item.variant_name,
                "quantity": float(item.quantity or 0),
                "unit": item.unit,
                "unit_price": float(item.unit_price or 0),
                "notes": item.notes,
            }
            for item in items
        ],
    }


def refresh_receipt_status(receipt: PurchaseReceipt, db: Session):
    db.flush()
    available = db.scalar(
        select(func.sum(PurchaseReceiptItem.available_quantity))
        .where(PurchaseReceiptItem.receipt_id == receipt.id)
    )
    receipt.status = "有未安排" if float(available or 0) > 0 else "已全部分配"


def normalize_outbound_item(item: OutboundOrderItem, db: Session):
    product = db.get(Product, item.product_id)
    if not product:
        raise HTTPException(status_code=400, detail="出库明细商品不存在")
    item.product_name = item.product_name or product.name
    if item.variant_id:
        variant = db.get(ProductVariant, item.variant_id)
        if not variant or variant.product_id != product.id:
            raise HTTPException(status_code=400, detail="出库明细规格不存在")
        item.variant_name = item.variant_name or variant_label(variant)
        item.unit = item.unit or variant.unit or product.unit
        item.unit_price = item.unit_price or variant.reference_purchase_price or product.reference_purchase_price
    else:
        item.unit = item.unit or product.purchase_unit or product.unit
        item.unit_price = item.unit_price or product.reference_purchase_price


def apply_outbound_stock(order: OutboundOrder, db: Session):
    items = db.scalars(select(OutboundOrderItem).where(OutboundOrderItem.order_id == order.id).order_by(OutboundOrderItem.id)).all()
    if not items:
        raise HTTPException(status_code=400, detail="出库单没有明细")
    for item in items:
        product = db.get(Product, item.product_id)
        if not product:
            raise HTTPException(status_code=400, detail="出库明细商品不存在")
        if item.variant_id:
            variant = db.get(ProductVariant, item.variant_id)
            if not variant:
                raise HTTPException(status_code=400, detail="出库明细规格不存在")
            before_stock = float(variant.stock or 0)
            if before_stock < item.quantity:
                raise HTTPException(status_code=400, detail=f"{item.product_name} {item.variant_name} 库存不足")
            variant.stock = before_stock - item.quantity
            product.stock = int(product_stock(product, db))
            after_stock = float(variant.stock or 0)
            unit = variant.unit or item.unit
            variant_name = item.variant_name or variant_label(variant)
        else:
            if product.package_conversion_enabled:
                variants = db.scalars(
                    select(ProductVariant)
                    .where(ProductVariant.product_id == product.id)
                    .order_by(ProductVariant.sort_order, ProductVariant.id)
                ).all()
                if not variants:
                    raise HTTPException(status_code=400, detail=f"{item.product_name} 已开启成套采购，但没有设置型号")
                before_stock = product_stock(product, db)
                if before_stock < item.quantity:
                    raise HTTPException(status_code=400, detail=f"{item.product_name} 成套库存不足")
                for variant in variants:
                    variant_before = float(variant.stock or 0)
                    reduce_quantity = item.quantity * float(variant.conversion_quantity or 1)
                    if variant_before < reduce_quantity:
                        raise HTTPException(status_code=400, detail=f"{item.product_name} {variant_label(variant)} 库存不足")
                    variant.stock = variant_before - reduce_quantity
                    db.add(
                        InventoryMovement(
                            product_id=product.id,
                            variant_id=variant.id,
                            product_name=item.product_name or product.name,
                            variant_name=variant_label(variant),
                            movement_type="成套拆分出库",
                            direction="出库",
                            quantity=reduce_quantity,
                            before_stock=variant_before,
                            after_stock=float(variant.stock or 0),
                            unit=variant.unit or product.unit,
                            unit_price=variant.reference_purchase_price,
                            total_amount=reduce_quantity * float(variant.reference_purchase_price or 0),
                            source_type="出库单",
                            source_no=order.order_no,
                            operator=order.handler,
                            notes=item.notes or order.notes,
                        )
                    )
                product.stock = int(product_stock(product, db))
                after_stock = float(product.stock or 0)
                unit = item.unit or product.purchase_unit or product.unit
                variant_name = "成套出库"
                db.add(
                    InventoryMovement(
                        product_id=product.id,
                        variant_id=None,
                        product_name=item.product_name or product.name,
                        variant_name=variant_name,
                        movement_type=order.outbound_type or "项目出库",
                        direction="出库",
                        quantity=item.quantity,
                        before_stock=before_stock,
                        after_stock=after_stock,
                        unit=unit,
                        unit_price=item.unit_price,
                        total_amount=item.quantity * item.unit_price,
                        source_type="出库单",
                        source_no=order.order_no,
                        operator=order.handler,
                        notes=item.notes or order.notes,
                    )
                )
                continue
            before_stock = float(product.stock or 0)
            if before_stock < item.quantity:
                raise HTTPException(status_code=400, detail=f"{item.product_name} 库存不足")
            product.stock = int(before_stock - item.quantity)
            after_stock = float(product.stock or 0)
            unit = item.unit or product.purchase_unit or product.unit
            variant_name = ""
        db.add(
            InventoryMovement(
                product_id=product.id,
                variant_id=item.variant_id,
                product_name=item.product_name or product.name,
                variant_name=variant_name,
                movement_type=order.outbound_type or "项目出库",
                direction="出库",
                quantity=item.quantity,
                before_stock=before_stock,
                after_stock=after_stock,
                unit=unit,
                unit_price=item.unit_price,
                total_amount=item.quantity * item.unit_price,
                source_type="出库单",
                source_no=order.order_no,
                operator=order.handler,
                notes=item.notes or order.notes,
            )
        )


@router.get("")
def list_inventory(
    keyword: str = Query(default="", max_length=100),
    low_stock_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    receipt_filters = [PurchaseReceiptItem.available_quantity > 0]
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        receipt_ids = select(PurchaseReceipt.id).where(
            or_(
                PurchaseReceipt.receipt_no.like(pattern),
                PurchaseReceipt.supplier.like(pattern),
                PurchaseReceipt.purchaser.like(pattern),
            )
        )
        receipt_filters.append(
            or_(
                PurchaseReceiptItem.product_name.like(pattern),
                PurchaseReceiptItem.variant_name.like(pattern),
                PurchaseReceiptItem.receipt_id.in_(receipt_ids),
            )
        )
    receipt_items = db.scalars(
        select(PurchaseReceiptItem)
        .where(*receipt_filters)
        .order_by(PurchaseReceiptItem.created_at.asc(), PurchaseReceiptItem.id.asc())
    ).all()
    items = []
    for row in receipt_items:
        receipt = db.get(PurchaseReceipt, row.receipt_id)
        product = db.get(Product, row.product_id)
        variant = db.get(ProductVariant, row.variant_id) if row.variant_id else None
        stock = float(row.available_quantity or 0)
        items.append(
            {
                "item_type": "receipt_balance",
                "receipt_id": row.receipt_id,
                "receipt_item_id": row.id,
                "receipt_no": receipt.receipt_no if receipt else "",
                "receipt_date": receipt.receipt_date.isoformat() if receipt and receipt.receipt_date else None,
                "supplier": receipt.supplier if receipt else "",
                "product_id": row.product_id,
                "variant_id": row.variant_id,
                "product_code": product.code if product else "",
                "variant_code": variant.code if variant else "",
                "product_name": row.product_name,
                "category": product.category if product else "",
                "specification": row.variant_name or (variant_label(variant) if variant else "默认"),
                "unit": row.unit,
                "stock": stock,
                "available_quantity": stock,
                "reference_purchase_price": float(row.unit_price or 0),
                "unit_price": float(row.unit_price or 0),
                "stock_value": stock * float(row.unit_price or 0),
                "status": "未安排",
            }
        )
    if low_stock_only:
        items = [item for item in items if item["stock"] <= 0]
    return {"items": items, "total": len(items)}

    filters = []
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        variant_product_ids = select(ProductVariant.product_id).where(
            or_(
                ProductVariant.code.like(pattern),
                ProductVariant.specification.like(pattern),
            )
        )
        filters.append(or_(Product.name.like(pattern), Product.code.like(pattern), Product.category.like(pattern), Product.id.in_(variant_product_ids)))

    products = db.scalars(select(Product).where(*filters).order_by(Product.category, Product.name, Product.id)).all()
    items = []
    for product in products:
        variants = db.scalars(
            select(ProductVariant)
            .where(ProductVariant.product_id == product.id)
            .order_by(ProductVariant.sort_order, ProductVariant.id)
        ).all()
        if product.package_conversion_enabled:
            items.append(
                {
                    "item_type": "bundle",
                    "product_id": product.id,
                    "variant_id": None,
                    "product_code": product.code,
                    "variant_code": "",
                    "product_name": product.name,
                    "category": product.category,
                    "specification": "成套采购",
                    "unit": product.purchase_unit or product.unit,
                    "stock": float(product.stock or 0),
                    "reference_purchase_price": float(product.reference_purchase_price or 0),
                    "status": product.status,
                }
            )
        if variants:
            for variant in variants:
                items.append(
                    {
                        "item_type": "variant",
                        "product_id": product.id,
                        "variant_id": variant.id,
                        "product_code": product.code,
                        "variant_code": variant.code,
                        "product_name": product.name,
                        "category": product.category,
                        "specification": variant_label(variant),
                        "unit": variant.unit or product.unit,
                        "stock": float(variant.stock or 0),
                        "reference_purchase_price": float(variant.reference_purchase_price or 0),
                        "status": variant.status,
                    }
                )
        elif not product.package_conversion_enabled:
            items.append(
                {
                    "item_type": "product",
                    "product_id": product.id,
                    "variant_id": None,
                    "product_code": product.code,
                    "variant_code": "",
                    "product_name": product.name,
                    "category": product.category,
                    "specification": product.specification or "默认",
                    "unit": product.unit,
                    "stock": float(product.stock or 0),
                    "reference_purchase_price": float(product.reference_purchase_price or 0),
                    "status": product.status,
                }
            )

    if low_stock_only:
        items = [item for item in items if item["stock"] <= 0]
    return {"items": items, "total": len(items)}


@router.get("/movements")
def list_movements(
    keyword: str = Query(default="", max_length=100),
    movement_type: str = Query(default="", max_length=32),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    filters = []
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(
            or_(
                InventoryMovement.product_name.like(pattern),
                InventoryMovement.variant_name.like(pattern),
                InventoryMovement.source_no.like(pattern),
                InventoryMovement.operator.like(pattern),
            )
        )
    if movement_type.strip():
        filters.append(InventoryMovement.movement_type == movement_type.strip())
    movements = db.scalars(select(InventoryMovement).where(*filters).order_by(InventoryMovement.id.desc()).limit(limit)).all()
    total = db.scalar(select(func.count()).select_from(InventoryMovement).where(*filters)) or 0
    return {"items": [serialize_movement(row) for row in movements], "total": total}


@router.post("/receipt-items/{receipt_item_id}/allocate")
def allocate_receipt_item(
    receipt_item_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    receipt_item = db.get(PurchaseReceiptItem, receipt_item_id)
    if not receipt_item:
        raise HTTPException(status_code=404, detail="收据余量不存在")
    receipt = db.get(PurchaseReceipt, receipt_item.receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="收据不存在")
    quantity = float(payload.get("quantity") or 0)
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="分配数量必须大于0")
    before_quantity = float(receipt_item.available_quantity or 0)
    if quantity > before_quantity:
        raise HTTPException(status_code=400, detail="分配数量不能超过未安排余量")

    project_id = int(payload["project_id"]) if payload.get("project_id") else None
    project_name = str(payload.get("project_name") or "").strip()
    business_order_id = int(payload["business_order_id"]) if payload.get("business_order_id") else None
    business_order_no = str(payload.get("business_order_no") or "").strip()

    business = None
    if business_order_id:
        business = db.get(BusinessOrder, business_order_id)
    elif business_order_no:
        business = db.scalar(select(BusinessOrder).where(BusinessOrder.order_no == business_order_no))
    if business:
        business_order_id = business.id
        business_order_no = business.order_no
        project_id = project_id or business.project_id
        project_name = project_name or business.project_name

    project = None
    if project_id:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=400, detail="项目不存在")
    elif project_name:
        project = db.scalar(select(Project).where(Project.name == project_name))
    if project:
        project_id = project.id
        project_name = project.name
    if not project_name and not business_order_no:
        raise HTTPException(status_code=400, detail="请填写项目或订单去向")

    receipt_item.available_quantity = before_quantity - quantity
    allocation = PurchaseReceiptAllocation(
        receipt_item_id=receipt_item.id,
        receipt_id=receipt.id,
        product_id=receipt_item.product_id,
        variant_id=receipt_item.variant_id,
        project_id=project_id,
        project_name=project_name,
        business_order_id=business_order_id,
        business_order_no=business_order_no,
        quantity=quantity,
        unit=receipt_item.unit,
        unit_price=float(receipt_item.unit_price or 0),
        total_amount=quantity * float(receipt_item.unit_price or 0),
        allocation_type="manual",
        operator=user.display_name or user.username,
        notes=str(payload.get("notes") or ""),
    )
    db.add(allocation)
    db.add(
        InventoryMovement(
            product_id=receipt_item.product_id,
            variant_id=receipt_item.variant_id,
            product_name=receipt_item.product_name,
            variant_name=receipt_item.variant_name,
            movement_type="收据余量分配",
            direction="出库",
            quantity=quantity,
            before_stock=before_quantity,
            after_stock=float(receipt_item.available_quantity or 0),
            unit=receipt_item.unit,
            unit_price=float(receipt_item.unit_price or 0),
            total_amount=quantity * float(receipt_item.unit_price or 0),
            source_type="采购收据",
            source_no=receipt.receipt_no,
            operator=user.display_name or user.username,
            notes=f"{project_name or business_order_no}；{payload.get('notes') or ''}".strip("；"),
        )
    )
    refresh_receipt_status(receipt, db)
    db.commit()
    return {
        "status": "allocated",
        "receipt_item_id": receipt_item.id,
        "allocated_quantity": quantity,
        "available_quantity": float(receipt_item.available_quantity or 0),
        "allocation_id": allocation.id,
    }


@router.get("/outbound-orders")
def list_outbound_orders(
    keyword: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    filters = []
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(OutboundOrder.order_no.like(pattern), OutboundOrder.project_name.like(pattern), OutboundOrder.handler.like(pattern)))
    orders = db.scalars(select(OutboundOrder).where(*filters).order_by(OutboundOrder.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(OutboundOrder).where(*filters)) or 0
    return {"items": [serialize_outbound(order, db) for order in orders], "total": total}


@router.post("/outbound-orders")
def create_outbound_order(
    payload: dict,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    order_no = str(payload.get("order_no") or "").strip()
    if not order_no:
        raise HTTPException(status_code=400, detail="请填写出库单号")
    if db.scalar(select(OutboundOrder).where(OutboundOrder.order_no == order_no)):
        raise HTTPException(status_code=409, detail="出库单号已存在")
    items_payload = payload.get("items") or []
    if not items_payload:
        raise HTTPException(status_code=400, detail="请添加出库明细")
    outbound_date = payload.get("outbound_date") or None
    if isinstance(outbound_date, str):
        outbound_date = date.fromisoformat(outbound_date) if outbound_date else None
    order = OutboundOrder(
        order_no=order_no,
        outbound_type=str(payload.get("outbound_type") or "项目领用"),
        project_name=str(payload.get("project_name") or ""),
        handler=str(payload.get("handler") or ""),
        outbound_date=outbound_date,
        notes=str(payload.get("notes") or ""),
    )
    db.add(order)
    db.flush()
    for entry in items_payload:
        quantity = float(entry.get("quantity") or 0)
        if quantity <= 0:
            raise HTTPException(status_code=400, detail="出库数量必须大于0")
        item = OutboundOrderItem(
            order_id=order.id,
            product_id=int(entry.get("product_id") or 0),
            variant_id=int(entry["variant_id"]) if entry.get("variant_id") else None,
            product_name=str(entry.get("product_name") or ""),
            variant_name=str(entry.get("variant_name") or ""),
            quantity=quantity,
            unit=str(entry.get("unit") or ""),
            unit_price=float(entry.get("unit_price") or 0),
            notes=str(entry.get("notes") or ""),
        )
        normalize_outbound_item(item, db)
        db.add(item)
    db.commit()
    db.refresh(order)
    return serialize_outbound(order, db)


@router.post("/outbound-orders/{order_id}/confirm")
def confirm_outbound_order(
    order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    order = db.get(OutboundOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="出库单不存在")
    if order.status == "已出库":
        raise HTTPException(status_code=400, detail="出库单已出库")
    apply_outbound_stock(order, db)
    order.status = "已出库"
    sync_business_order_from_outbound(order, db)
    db.commit()
    db.refresh(order)
    return serialize_outbound(order, db)


@router.post("/adjust")
def adjust_inventory(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    receipt_item_id = payload.get("receipt_item_id")
    if receipt_item_id:
        receipt_item = db.get(PurchaseReceiptItem, int(receipt_item_id))
        if not receipt_item:
            raise HTTPException(status_code=404, detail="收据余量不存在")
        new_stock = float(payload.get("new_stock") or payload.get("available_quantity") or 0)
        if new_stock < 0:
            raise HTTPException(status_code=400, detail="库存不能小于0")
        before_stock = float(receipt_item.available_quantity or 0)
        receipt_item.available_quantity = new_stock
        difference = new_stock - before_stock
        receipt = db.get(PurchaseReceipt, receipt_item.receipt_id)
        if receipt:
            receipt.status = "有未安排" if new_stock > 0 else "已全部分配"
        db.add(
            InventoryMovement(
                product_id=receipt_item.product_id,
                variant_id=receipt_item.variant_id,
                product_name=receipt_item.product_name,
                variant_name=receipt_item.variant_name,
                movement_type="收据余量盘点",
                direction="入库" if difference >= 0 else "出库",
                quantity=abs(difference),
                before_stock=before_stock,
                after_stock=new_stock,
                unit=receipt_item.unit,
                unit_price=receipt_item.unit_price,
                total_amount=abs(difference) * float(receipt_item.unit_price or 0),
                source_type="收据余量",
                source_no=receipt.receipt_no if receipt else str(receipt_item.receipt_id),
                operator=user.display_name or user.username,
                notes=str(payload.get("notes") or ""),
            )
        )
        db.commit()
        return {
            "status": "ok",
            "item": {
                "receipt_item_id": receipt_item.id,
                "receipt_id": receipt_item.receipt_id,
                "stock": float(receipt_item.available_quantity or 0),
                "before_stock": before_stock,
                "difference": difference,
            },
        }

    product_id = int(payload.get("product_id") or 0)
    variant_id = payload.get("variant_id")
    new_stock = float(payload.get("new_stock") or 0)
    if new_stock < 0:
        raise HTTPException(status_code=400, detail="库存不能小于0")

    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    if variant_id:
        variant = db.get(ProductVariant, int(variant_id))
        if not variant or variant.product_id != product.id:
            raise HTTPException(status_code=404, detail="规格不存在")
        before_stock = float(variant.stock or 0)
        variant.stock = new_stock
        if not product.package_conversion_enabled:
            product.stock = int(product_stock(product, db))
        after_stock = float(variant.stock or 0)
        item = {"product_id": product.id, "variant_id": variant.id, "stock": variant.stock}
        variant_name = variant_label(variant)
        unit = variant.unit or product.unit
    else:
        before_stock = float(product.stock or 0)
        product.stock = int(new_stock)
        after_stock = float(product.stock or 0)
        item = {"product_id": product.id, "variant_id": None, "stock": float(product.stock or 0)}
        variant_name = ""
        unit = product.purchase_unit or product.unit

    difference = after_stock - before_stock
    db.add(
        InventoryMovement(
            product_id=product.id,
            variant_id=int(variant_id) if variant_id else None,
            product_name=product.name,
            variant_name=variant_name,
            movement_type="盘点调整",
            direction="入库" if difference >= 0 else "出库",
            quantity=abs(difference),
            before_stock=before_stock,
            after_stock=after_stock,
            unit=unit,
            unit_price=0,
            total_amount=0,
            source_type="库存盘点",
            source_no="",
            operator=user.display_name or user.username,
            notes=str(payload.get("notes") or ""),
        )
    )

    db.commit()
    return {"status": "ok", "item": item}
