import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import (
    ApprovalRequest,
    ApprovalRule,
    BusinessOrder,
    BusinessOrderItem,
    Contract,
    Customer,
    Employee,
    OutboundOrder,
    OutboundOrderItem,
    Product,
    ProductVariant,
    Project,
    ProjectLocation,
    ProjectPlant,
    ProjectPlantChange,
    PurchaseOrder,
    PurchaseOrderItem,
    ScheduleTask,
    User,
)
from ..permissions import accessible_project_ids, can_access_module, can_access_project, has_full_access, require_module
from .purchases import default_purchaser


router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


TYPE_MAP = {
    "lease": "租赁订单",
    "sales": "销售订单",
    "exchange": "换花订单",
    "maintenance": "养护订单",
    "delivery": "配送订单",
    "gift": "赠送订单",
    "withdraw": "撤花订单",
}
ORDER_PREFIX = {
    "租赁订单": "ZB",
    "销售订单": "XS",
    "换花订单": "HH",
    "养护订单": "YH",
    "配送订单": "PS",
    "赠送订单": "ZS",
    "撤花订单": "CH",
}

# 审批机制还没有最终确定，先保留代码但暂停自动触发。
APPROVAL_FLOW_ENABLED = False


def next_business_order_no(order_type: str, db: Session, preferred: str = "") -> str:
    prefix = ORDER_PREFIX.get(order_type, "DD")
    preferred = (preferred or "").strip().upper().replace("-", "")
    if re.fullmatch(rf"{prefix}\d{{6}}", preferred) and not db.scalar(select(BusinessOrder.id).where(BusinessOrder.order_no == preferred)):
        return preferred
    rows = db.scalars(select(BusinessOrder.order_no).where(BusinessOrder.order_no.like(f"{prefix}%"))).all()
    max_no = 0
    for value in rows:
        match = re.fullmatch(rf"{prefix}(\d{{6}})", str(value or "").upper().replace("-", ""))
        if match:
            max_no = max(max_no, int(match.group(1)))
    while True:
        max_no += 1
        candidate = f"{prefix}{max_no:06d}"
        if not db.scalar(select(BusinessOrder.id).where(BusinessOrder.order_no == candidate)):
            return candidate


def parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def variant_label(variant: ProductVariant) -> str:
    return variant.specification or variant.code


def source_no(prefix: str, order_no: str) -> str:
    return f"{prefix}-{order_no}"[:64]


def order_requires_outbound(order: BusinessOrder) -> bool:
    """当前公司流程里仓库只确认入库，订单主流程不再要求手动出库。"""
    return False


def order_initial_status(order: BusinessOrder) -> str:
    if order.status in {"已完成", "已取消", "已驳回", "待审批"}:
        return order.status
    if order.need_purchase:
        return "待采购"
    if order.need_delivery:
        return "待配送"
    return "已完成"


def sync_order_status_from_flow(order: BusinessOrder, db: Session):
    if order.status in {"已完成", "已取消", "已驳回", "待审批"}:
        return
    purchase = db.scalar(select(PurchaseOrder).where(PurchaseOrder.order_no == source_no("CG", order.order_no)))
    outbound = db.scalar(select(OutboundOrder).where(OutboundOrder.order_no == source_no("CK", order.order_no)))
    schedule = db.scalar(
        select(ScheduleTask)
        .where(or_(ScheduleTask.task_no == source_no("RC", order.order_no), ScheduleTask.task_no == source_no("RC", source_no("CK", order.order_no))))
        .order_by(ScheduleTask.id.desc())
    )
    if schedule:
        if schedule.status in {"已完成"}:
            order.status = "已完成"
            apply_project_plant_linkage(order, db)
        elif schedule.status in {"已送达"}:
            order.status = "配送中"
        elif schedule.status in {"配送中", "已出发"}:
            order.status = "配送中"
        elif schedule.status in {"已发布", "待配送", "待发布"}:
            order.status = "待配送"
        return
    if outbound:
        if outbound.status in {"已出库", "配送中", "已送达"}:
            order.status = "待配送" if order.need_delivery else "已完成"
        else:
            order.status = "待配送"
        return
    if purchase:
        if purchase.status == "已入库":
            order.status = "待配送" if order.need_delivery else "已完成"
        elif purchase.status == "待入库":
            order.status = "待入库"
        else:
            order.status = "待采购"
        return
    order.status = order_initial_status(order)


def order_amount(order: BusinessOrder, db: Session) -> float:
    items = db.scalars(select(BusinessOrderItem).where(BusinessOrderItem.order_id == order.id)).all()
    return float(sum((item.amount or item.quantity * item.unit_price or 0) for item in items))


def annual_exchange_amount(order: BusinessOrder, current_amount: float, db: Session) -> float:
    year = (order.order_date or date.today()).year
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    orders = db.scalars(
        select(BusinessOrder).where(
            BusinessOrder.project_id == order.project_id,
            BusinessOrder.order_type.like("%换花%"),
            BusinessOrder.order_date >= start,
            BusinessOrder.order_date <= end,
            BusinessOrder.id != order.id,
        )
    ).all()
    return current_amount + sum(order_amount(item, db) for item in orders)


def ensure_order_approval(order: BusinessOrder, db: Session):
    if not APPROVAL_FLOW_ENABLED:
        return
    if not order.project_id:
        return
    rule = db.scalar(select(ApprovalRule).where(ApprovalRule.project_id == order.project_id, ApprovalRule.status == "启用"))
    if not rule:
        return
    reasons = []
    amount = order_amount(order, db)
    if order.need_purchase and rule.purchase_requires_approval:
        reasons.append("该项目设置了采购需求必须审批")
    if "换花" in order.order_type and rule.exchange_annual_limit:
        annual_amount = annual_exchange_amount(order, amount, db)
        if annual_amount >= float(rule.exchange_annual_limit or 0):
            reasons.append(f"换花年度累计 {annual_amount:.2f} 达到审批额度 {float(rule.exchange_annual_limit or 0):.2f}")
    if not reasons:
        return
    request_no = source_no("SP", order.order_no)
    if db.scalar(select(ApprovalRequest).where(ApprovalRequest.request_no == request_no)):
        order.status = "待审批"
        return
    db.add(
        ApprovalRequest(
            request_no=request_no,
            approval_type="订单审批",
            source_type="订单",
            source_id=order.id,
            source_no=order.order_no,
            project_id=order.project_id,
            project_name=order.project_name,
            applicant=order.requester,
            amount=amount,
            reason="；".join(reasons),
            approver_role=rule.approver_role,
            approver_name=rule.approver_name,
            status="待审批",
        )
    )
    order.status = "待审批"


def serialize_order(order: BusinessOrder, db: Session):
    items = db.scalars(select(BusinessOrderItem).where(BusinessOrderItem.order_id == order.id).order_by(BusinessOrderItem.id)).all()
    project = db.get(Project, order.project_id) if order.project_id else None
    customer = db.get(Customer, project.customer_id) if project else None
    supervisor = db.get(Employee, project.supervisor_id) if project and project.supervisor_id else None
    contract = db.scalar(
        select(Contract)
        .where(Contract.project_id == project.id)
        .order_by(Contract.effective_date.desc(), Contract.id.desc())
    ) if project else None
    progress = workflow_progress(order, db)
    current_step = current_order_step(order, progress)
    return {
        "id": order.id,
        "order_no": order.order_no,
        "order_type": order.order_type,
        "project_id": order.project_id,
        "project_name": order.project_name,
        "customer_name": order.customer_name,
        "requester": order.requester,
        "contact_phone": order.contact_phone,
        "order_date": order.order_date.isoformat() if order.order_date else None,
        "expected_date": order.expected_date.isoformat() if order.expected_date else None,
        "priority": order.priority,
        "need_purchase": order.need_purchase,
        "need_delivery": order.need_delivery,
        "status": order.status,
        "current_step": current_step["step"],
        "current_status": current_step["status"],
        "current_actor": current_step["actor"],
        "current_ref_no": current_step["ref_no"],
        "current_description": current_step["description"],
        "notes": order.notes,
        "project_address": project.address if project else "",
        "project_business_types": project.business_types if project else order.order_type,
        "project_supervisor_name": supervisor.name if supervisor else "",
        "project_supervisor_phone": supervisor.phone if supervisor else "",
        "customer_contact_person": customer.contact_person if customer else "",
        "customer_phone": customer.phone if customer else "",
        "contract_amount": float(contract.amount or 0) if contract else 0,
        "contract_billing_cycle": contract.billing_cycle if contract else "",
        "contract_effective_date": contract.effective_date.isoformat() if contract and contract.effective_date else None,
        "contract_end_date": contract.end_date.isoformat() if contract and contract.end_date else None,
        "contract_billing_start_date": contract.billing_start_date.isoformat() if contract and contract.billing_start_date else None,
        "progress": progress,
        "created_at": order.created_at.isoformat() if order.created_at else "",
        "items": [
            (
                lambda product, variant: {
                "id": item.id,
                "order_id": item.order_id,
                "product_id": item.product_id,
                "variant_id": item.variant_id,
                "product_name": item.product_name,
                "variant_name": item.variant_name,
                "product_image_url": product.image_url if product else "",
                "variant_image_url": variant.image_url if variant else "",
                "location_text": item.location_text,
                "quantity": float(item.quantity or 0),
                "unit": item.unit,
                "unit_price": float(item.unit_price or 0),
                "amount": float(item.amount or 0),
                "notes": item.notes,
                }
            )(db.get(Product, item.product_id) if item.product_id else None, db.get(ProductVariant, item.variant_id) if item.variant_id else None)
            for item in items
        ],
    }


def normalize_order_item(item: BusinessOrderItem, db: Session):
    if not item.product_id:
        item.amount = item.quantity * item.unit_price
        return
    product = db.get(Product, item.product_id)
    if not product:
        raise HTTPException(status_code=400, detail="订单明细商品不存在")
    item.product_name = item.product_name or product.name
    if item.variant_id:
        variant = db.get(ProductVariant, item.variant_id)
        if not variant or variant.product_id != product.id:
            raise HTTPException(status_code=400, detail="订单明细规格不存在")
        item.variant_name = item.variant_name or variant_label(variant)
        item.unit = item.unit or variant.unit or product.unit
        item.unit_price = item.unit_price or variant.sale_price or variant.monthly_rental_price or product.sale_price
    else:
        item.unit = item.unit or product.unit
        item.unit_price = item.unit_price or product.sale_price
    item.amount = item.quantity * item.unit_price


def cost_price(item: BusinessOrderItem, db: Session) -> float:
    product = db.get(Product, item.product_id) if item.product_id else None
    if item.variant_id:
        variant = db.get(ProductVariant, item.variant_id)
        if variant:
            return float(variant.reference_purchase_price or product.reference_purchase_price if product else 0)
    if product:
        return float(product.reference_purchase_price or 0)
    return 0


def item_unit(item: BusinessOrderItem, db: Session) -> str:
    product = db.get(Product, item.product_id) if item.product_id else None
    if item.variant_id:
        variant = db.get(ProductVariant, item.variant_id)
        if variant:
            return variant.unit or item.unit
    if product:
        return item.unit or product.unit or product.purchase_unit
    return item.unit


def order_item_available_stock(item: BusinessOrderItem, db: Session) -> float:
    if not item.product_id:
        return 0
    if item.variant_id:
        variant = db.get(ProductVariant, item.variant_id)
        return float(variant.stock or 0) if variant else 0
    product = db.get(Product, item.product_id)
    return float(product.stock or 0) if product else 0


def order_items_all_in_stock(items: list[BusinessOrderItem], db: Session) -> bool:
    product_items = [item for item in items if item.product_id]
    if not product_items:
        return False
    return all(order_item_available_stock(item, db) >= float(item.quantity or 0) for item in product_items)


def replace_items(order: BusinessOrder, entries: list[dict], db: Session):
    for old_item in db.scalars(select(BusinessOrderItem).where(BusinessOrderItem.order_id == order.id)).all():
        db.delete(old_item)
    db.flush()
    for entry in entries:
        quantity = float(entry.get("quantity") or 0)
        if quantity <= 0:
            raise HTTPException(status_code=400, detail="订单明细数量必须大于0")
        item = BusinessOrderItem(
            order_id=order.id,
            product_id=int(entry["product_id"]) if entry.get("product_id") else None,
            variant_id=int(entry["variant_id"]) if entry.get("variant_id") else None,
            product_name=str(entry.get("product_name") or ""),
            variant_name=str(entry.get("variant_name") or ""),
            location_text=str(entry.get("location_text") or ""),
            quantity=quantity,
            unit=str(entry.get("unit") or ""),
            unit_price=float(entry.get("unit_price") or 0),
            notes=str(entry.get("notes") or ""),
        )
        normalize_order_item(item, db)
        db.add(item)


def resolve_order_location(order: BusinessOrder, item: BusinessOrderItem, db: Session) -> ProjectLocation | None:
    if not order.project_id:
        return None
    locations = db.scalars(
        select(ProjectLocation)
        .where(ProjectLocation.project_id == order.project_id)
        .order_by(ProjectLocation.location_type.desc(), ProjectLocation.sort_order, ProjectLocation.id)
    ).all()
    if not locations:
        return None
    text = (item.location_text or "").strip()
    if text:
        for location in sorted(locations, key=lambda entry: len(entry.name or ""), reverse=True):
            if ("区域" in (location.location_type or "") or "办公室" in (location.name or "")) and (location.name == text or location.name in text):
                return location
        for location in locations:
            if location.name == text or location.name in text:
                return location
    for location in locations:
        if "区域" in (location.location_type or ""):
            return location
    for location in locations:
        if "办公室" in (location.location_type or ""):
            return location
    return locations[0]


def find_project_plant(order: BusinessOrder, item: BusinessOrderItem, location: ProjectLocation | None, db: Session) -> ProjectPlant | None:
    if not order.project_id or not item.product_id:
        return None
    filters = [
        ProjectPlant.project_id == order.project_id,
        ProjectPlant.product_id == int(item.product_id),
        ProjectPlant.status == "在场",
    ]
    if location:
        filters.append(ProjectPlant.location_id == location.id)
    if item.variant_name:
        filters.append(ProjectPlant.specification == item.variant_name)
    return db.scalar(select(ProjectPlant).where(*filters).order_by(ProjectPlant.id.desc()))


def append_note(original: str, addition: str) -> str:
    return f"{original}\n{addition}".strip() if original else addition


def compact_text(*values) -> str:
    return " ".join(str(value or "") for value in values)


def item_display_name(item: BusinessOrderItem) -> str:
    if item.product_name and item.variant_name:
        return f"{item.product_name}（{item.variant_name}）"
    return item.product_name or item.variant_name or "未命名明细"


def is_pot_change_line(order: BusinessOrder, item: BusinessOrderItem, db: Session) -> bool:
    product = db.get(Product, item.product_id) if item.product_id else None
    text = compact_text(
        order.order_type,
        order.notes,
        item.notes,
        item.product_name,
        item.variant_name,
        product.name if product else "",
        product.category if product else "",
    )
    if "盆景" in text and "换盆" not in text and "花盆" not in text:
        return False
    return "换盆" in text or "花盆" in text


def can_sync_to_project_plant(item: BusinessOrderItem, db: Session) -> bool:
    product = db.get(Product, item.product_id) if item.product_id else None
    if not product:
        return False
    text = compact_text(product.category, product.name, item.product_name, item.variant_name)
    if any(word in text for word in ["花盆", "农药", "药", "肥料", "工具", "服务", "运费", "货拉拉"]):
        return False
    return any(word in text for word in ["植物", "盆景", "绿萝", "发财树", "幸福树", "天堂鸟", "绿植"])


def find_location_project_plant(order: BusinessOrder, location: ProjectLocation | None, db: Session) -> ProjectPlant | None:
    if not order.project_id or not location:
        return None
    return db.scalar(
        select(ProjectPlant)
        .where(
            ProjectPlant.project_id == order.project_id,
            ProjectPlant.location_id == location.id,
            ProjectPlant.status == "在场",
        )
        .order_by(ProjectPlant.id.desc())
    )


def add_plant_change(
    db: Session,
    plant: ProjectPlant,
    order: BusinessOrder,
    change_type: str,
    quantity_before: float,
    quantity_after: float,
    pot_before: str = "",
    pot_after: str = "",
    notes: str = "",
):
    db.add(
        ProjectPlantChange(
            project_id=plant.project_id,
            plant_id=plant.id,
            location_id=plant.location_id,
            product_id=plant.product_id,
            change_type=change_type,
            source_type="订单",
            source_no=order.order_no,
            quantity_before=float(quantity_before or 0),
            quantity_after=float(quantity_after or 0),
            quantity_delta=float(quantity_after or 0) - float(quantity_before or 0),
            unit=plant.unit,
            pot_before=pot_before,
            pot_after=pot_after,
            operator=order.requester or "",
            notes=notes,
        )
    )


def apply_project_plant_linkage(order: BusinessOrder, db: Session):
    if not order.project_id:
        return
    if not any(label in order.order_type for label in ["租赁", "租摆", "换花", "撤花"]):
        return
    project = db.get(Project, order.project_id)
    if not project:
        return
    items = db.scalars(select(BusinessOrderItem).where(BusinessOrderItem.order_id == order.id).order_by(BusinessOrderItem.id)).all()
    today = date.today()
    for item in items:
        if not item.product_id:
            continue
        if not can_sync_to_project_plant(item, db) and not is_pot_change_line(order, item, db):
            order.notes = append_note(
                order.notes,
                f"{today.isoformat()} 明细 {item_display_name(item)} 非植物类商品，只计入订单/成本，不写入项目植物台账",
            )
            continue
        location = resolve_order_location(order, item, db)
        if not location:
            continue
        existing = find_project_plant(order, item, location, db)
        quantity = float(item.quantity or 0)
        if quantity <= 0:
            continue
        if is_pot_change_line(order, item, db):
            target = existing or find_location_project_plant(order, location, db)
            if target:
                quantity_before = float(target.quantity or 0)
                pot_before = target.decorative_pot or ""
                target.decorative_pot = item_display_name(item)
                target.notes = append_note(
                    target.notes,
                    f"{today.isoformat()} 由订单 {order.order_no} 更换花盆为 {item_display_name(item)}，数量 {quantity:g}{item.unit}；花盆成本由订单/出库计入项目成本",
                )
                add_plant_change(
                    db,
                    target,
                    order,
                    "换盆",
                    quantity_before,
                    float(target.quantity or 0),
                    pot_before,
                    target.decorative_pot,
                    f"更换花盆为 {item_display_name(item)}，数量 {quantity:g}{item.unit}",
                )
            else:
                order.notes = append_note(
                    order.notes,
                    f"{today.isoformat()} 花盆明细 {item_display_name(item)} 未匹配到项目植物，请在项目植物清单手工选择更新",
                )
            continue
        if "撤花" in order.order_type:
            if existing:
                quantity_before = float(existing.quantity or 0)
                existing.quantity = max(0, float(existing.quantity or 0) - quantity)
                existing.notes = append_note(existing.notes, f"{today.isoformat()} 由撤花单 {order.order_no} 撤出 {quantity:g}{item.unit}")
                if existing.quantity <= 0:
                    existing.status = "已撤场"
                add_plant_change(
                    db,
                    existing,
                    order,
                    "撤花",
                    quantity_before,
                    float(existing.quantity or 0),
                    existing.decorative_pot or "",
                    existing.decorative_pot or "",
                    f"撤出 {quantity:g}{item.unit}，旧植物默认丢弃",
                )
            continue
        if "换花" in order.order_type:
            if existing:
                quantity_before = float(existing.quantity or 0)
                existing.notes = append_note(existing.notes, f"{today.isoformat()} 由换花单 {order.order_no} 完成更换 {quantity:g}{item.unit}；旧植物默认丢弃")
                existing.entry_date = today
                add_plant_change(
                    db,
                    existing,
                    order,
                    "换花",
                    quantity_before,
                    float(existing.quantity or 0),
                    existing.decorative_pot or "",
                    existing.decorative_pot or "",
                    f"完成更换 {quantity:g}{item.unit}；旧植物默认丢弃",
                )
            else:
                new_plant = ProjectPlant(
                    project_id=project.id,
                    location_id=location.id,
                    product_id=int(item.product_id),
                    specification=item.variant_name or "",
                    quantity=quantity,
                    unit=item.unit,
                    decorative_pot="",
                    source=project.plant_source,
                    entry_date=today,
                    billing_start_date=today,
                    status="在场",
                    notes=f"由换花单 {order.order_no} 自动生成；旧植物默认丢弃",
                )
                db.add(new_plant)
                db.flush()
                add_plant_change(
                    db,
                    new_plant,
                    order,
                    "换花新增",
                    0,
                    float(new_plant.quantity or 0),
                    "",
                    new_plant.decorative_pot or "",
                    f"换花后新增 {quantity:g}{item.unit}；旧植物默认丢弃",
                )
            continue
        if "租赁" in order.order_type or "租摆" in order.order_type:
            if existing:
                quantity_before = float(existing.quantity or 0)
                existing.quantity = float(existing.quantity or 0) + quantity
                existing.notes = append_note(existing.notes, f"{today.isoformat()} 由租摆单 {order.order_no} 增加 {quantity:g}{item.unit}")
                add_plant_change(
                    db,
                    existing,
                    order,
                    "租摆增加",
                    quantity_before,
                    float(existing.quantity or 0),
                    existing.decorative_pot or "",
                    existing.decorative_pot or "",
                    f"租摆进场增加 {quantity:g}{item.unit}",
                )
            else:
                new_plant = ProjectPlant(
                    project_id=project.id,
                    location_id=location.id,
                    product_id=int(item.product_id),
                    specification=item.variant_name or "",
                    quantity=quantity,
                    unit=item.unit,
                    decorative_pot="",
                    source=project.plant_source,
                    entry_date=today,
                    billing_start_date=order.order_date or today,
                    status="在场",
                    notes=f"由租摆单 {order.order_no} 完成后自动入场",
                )
                db.add(new_plant)
                db.flush()
                add_plant_change(
                    db,
                    new_plant,
                    order,
                    "租摆进场",
                    0,
                    float(new_plant.quantity or 0),
                    "",
                    new_plant.decorative_pot or "",
                    f"租摆单完成后自动入场 {quantity:g}{item.unit}",
                )


def workflow_progress(order: BusinessOrder, db: Session) -> list[dict]:
    approval_no = source_no("SP", order.order_no)
    purchase_no = source_no("CG", order.order_no)
    outbound_no = source_no("CK", order.order_no)
    direct_schedule_no = source_no("RC", order.order_no)
    outbound_schedule_no = source_no("RC", outbound_no)

    approval = db.scalar(select(ApprovalRequest).where(ApprovalRequest.request_no == approval_no))
    purchase = db.scalar(select(PurchaseOrder).where(PurchaseOrder.order_no == purchase_no))
    outbound = db.scalar(select(OutboundOrder).where(OutboundOrder.order_no == outbound_no))
    schedule = db.scalar(
        select(ScheduleTask)
        .where(or_(ScheduleTask.task_no == direct_schedule_no, ScheduleTask.task_no == outbound_schedule_no))
        .order_by(ScheduleTask.id.desc())
    )
    schedule_driver = db.get(Employee, schedule.driver_id) if schedule and schedule.driver_id else None

    nodes: list[dict] = []
    if approval or order.status in {"待审批", "已驳回"}:
        approval_status = approval.status if approval else order.status
        nodes.append(
            {
                "key": "approval",
                "label": "审批",
                "status": approval_status,
                "ref_no": approval.request_no if approval else approval_no,
                "actor": approval.approver_name or approval.approver_role if approval else "",
                "date": approval.decided_at.date().isoformat() if approval and approval.decided_at else "",
                "description": approval.reason if approval else "订单需要审批",
                "state": "done" if approval_status == "已通过" else "rejected" if approval_status in {"已驳回", "驳回"} else "active",
            }
        )
    if order.need_purchase or purchase:
        purchase_status = purchase.status if purchase else "未生成"
        nodes.append(
            {
                "key": "purchase",
                "label": "采购",
                "status": purchase_status,
                "ref_no": purchase.order_no if purchase else purchase_no,
                "actor": purchase.purchaser if purchase else "",
                "date": purchase.purchase_date.isoformat() if purchase and purchase.purchase_date else "",
                "description": purchase.supplier if purchase else "还没有生成采购单",
                "state": "done" if purchase_status == "已入库" else "todo" if purchase_status == "未生成" else "active",
            }
        )
        nodes.append(
            {
                "key": "inbound",
                "label": "入库",
                "status": "已入库" if purchase_status == "已入库" else "待入库" if purchase_status == "待入库" else "未到达",
                "ref_no": purchase.order_no if purchase else purchase_no,
                "actor": purchase.purchaser if purchase else "",
                "date": purchase.purchase_date.isoformat() if purchase and purchase.purchase_date else "",
                "description": "采购单已确认入库" if purchase_status == "已入库" else "等待仓管确认入库" if purchase_status == "待入库" else "采购还未到达入库节点",
                "state": "done" if purchase_status == "已入库" else "active" if purchase_status == "待入库" else "todo",
            }
        )

    if False and (order_requires_outbound(order) or outbound):
        outbound_status = outbound.status if outbound else "未生成"
        nodes.append(
            {
                "key": "outbound",
                "label": "出库",
                "status": outbound_status,
                "ref_no": outbound.order_no if outbound else outbound_no,
                "actor": outbound.handler if outbound else "",
                "date": outbound.outbound_date.isoformat() if outbound and outbound.outbound_date else "",
                "description": outbound.outbound_type if outbound else "还没有生成出库单",
                "state": "done" if outbound_status in {"已出库", "配送中", "已送达", "已完成"} else "todo" if outbound_status == "未生成" else "active",
            }
        )
    if order.need_delivery or schedule:
        schedule_status = schedule.status if schedule else "未生成"
        nodes.append(
            {
                "key": "delivery",
                "label": "配送",
                "status": schedule_status,
                "ref_no": schedule.task_no if schedule else direct_schedule_no,
                "actor": schedule_driver.name if schedule_driver else "",
                "date": schedule.schedule_date.isoformat() if schedule else "",
                "description": schedule.item_summary if schedule else "还没有生成每日安排",
                "state": "done" if schedule_status == "已完成" else "todo" if schedule_status in {"未生成", "待发布"} else "active",
            }
        )
    return nodes


def current_order_step(order: BusinessOrder, progress: list[dict]) -> dict:
    closed_status = {"已完成", "已取消", "已驳回", "宸插畬鎴?", "宸插彇娑?", "宸查┏鍥?"}
    if order.status in closed_status:
        return {
            "step": order.status,
            "status": order.status,
            "actor": "",
            "ref_no": order.order_no,
            "description": "订单已结束",
        }

    if order.status in {"待审批", "寰呭鎵?"}:
        approval = next((node for node in progress if node.get("key") == "approval"), {})
        return {
            "step": "待审批",
            "status": approval.get("status") or order.status,
            "actor": approval.get("actor") or "审批人",
            "ref_no": approval.get("ref_no") or order.order_no,
            "description": approval.get("description") or "等待审批通过后继续处理",
        }

    label_map = {
        ("approval", "active"): ("待审批", "审批人"),
        ("purchase", "todo"): ("待采购", "客服/主管"),
        ("purchase", "active"): ("采购中", "采购员"),
        ("inbound", "active"): ("待入库", "仓管"),
        ("outbound", "todo"): ("待配送", "客服/主管"),
        ("outbound", "active"): ("待配送", "客服/主管"),
        ("delivery", "todo"): ("待配送", "客服/主管"),
        ("delivery", "active"): ("配送中", "司机/跟车"),
    }

    for node in progress:
        state = node.get("state")
        key = node.get("key")
        status = str(node.get("status") or "")
        if state == "active" or (key, state) in label_map:
            step, default_actor = label_map.get((key, state), (node.get("label") or "处理中", "相关人员"))
            if key == "delivery" and status == "已送达":
                step = "配送中"
                status = "配送中"
            return {
                "step": step,
                "status": status or "处理中",
                "actor": node.get("actor") or default_actor,
                "ref_no": node.get("ref_no") or order.order_no,
                "description": node.get("description") or "",
            }

    for node in progress:
        if node.get("state") == "todo":
            step, default_actor = label_map.get((node.get("key"), "todo"), (node.get("label") or "待处理", "相关人员"))
            return {
                "step": step,
                "status": node.get("status") or "待处理",
                "actor": node.get("actor") or default_actor,
                "ref_no": node.get("ref_no") or order.order_no,
                "description": node.get("description") or "",
            }

    return {
        "step": order.status or "待处理",
        "status": order.status or "待处理",
        "actor": order.requester or "",
        "ref_no": order.order_no,
        "description": order.notes or "",
    }


@router.get("")
def list_orders(
    order_type: str = Query(default="", max_length=32),
    keyword: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_module(user, "orders")
    filters = []
    project_ids = accessible_project_ids(user, db)
    if project_ids is not None:
        if not project_ids:
            return {"items": [], "total": 0}
        filters.append(BusinessOrder.project_id.in_(project_ids))
    normalized_type = TYPE_MAP.get(order_type, order_type)
    if normalized_type.strip():
        filters.append(BusinessOrder.order_type == normalized_type.strip())
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(
            or_(
                BusinessOrder.order_no.like(pattern),
                BusinessOrder.project_name.like(pattern),
                BusinessOrder.customer_name.like(pattern),
                BusinessOrder.requester.like(pattern),
            )
        )
    orders = db.scalars(select(BusinessOrder).where(*filters).order_by(BusinessOrder.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(BusinessOrder).where(*filters)) or 0
    return {"items": [serialize_order(order, db) for order in orders], "total": total}


@router.post("")
def create_order(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_module(user, "orders")
    entries = payload.get("items") or []
    if not entries:
        raise HTTPException(status_code=400, detail="请添加订单明细")

    order_type = TYPE_MAP.get(str(payload.get("order_type") or ""), str(payload.get("order_type") or "租赁订单"))
    order_no = next_business_order_no(order_type, db, str(payload.get("order_no") or ""))
    project_id = int(payload["project_id"]) if payload.get("project_id") else None
    project_name = str(payload.get("project_name") or "")
    if project_id:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=400, detail="项目不存在")
        if not can_access_project(user, project_id, db):
            raise HTTPException(status_code=403, detail="无权为该项目下单")
        project_name = project_name or project.name
    elif not has_full_access(user):
        raise HTTPException(status_code=403, detail="当前角色必须选择自己负责范围内的项目")
    order = BusinessOrder(
        order_no=order_no,
        order_type=order_type,
        project_id=project_id,
        project_name=project_name,
        customer_name=str(payload.get("customer_name") or ""),
        requester=str(payload.get("requester") or ""),
        contact_phone=str(payload.get("contact_phone") or ""),
        order_date=parse_date(payload.get("order_date")),
        expected_date=parse_date(payload.get("expected_date")),
        priority=str(payload.get("priority") or "普通"),
        need_purchase=bool(payload.get("need_purchase") or False),
        need_delivery=bool(payload.get("need_delivery") if payload.get("need_delivery") is not None else True),
        status=str(payload.get("status") or "待处理"),
        notes=str(payload.get("notes") or ""),
    )
    db.add(order)
    db.flush()
    replace_items(order, entries, db)
    db.flush()
    ensure_order_approval(order, db)
    sync_order_status_from_flow(order, db)
    db.commit()
    db.refresh(order)
    return serialize_order(order, db)


@router.post("/mobile-exchange-request")
def mobile_exchange_request(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if not (can_access_module(user, "schedule_workflow") or can_access_module(user, "orders")):
        raise HTTPException(status_code=403, detail="无权提交手机端换花申请")
    project_id = int(payload["project_id"]) if payload.get("project_id") else None
    if not project_id:
        raise HTTPException(status_code=400, detail="请选择项目")
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=400, detail="项目不存在")
    if not can_access_project(user, project_id, db):
        raise HTTPException(status_code=403, detail="无权为该项目报单")

    quantity = float(payload.get("quantity") or 1)
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="数量必须大于0")
    request_type = str(payload.get("request_type") or "换花")
    product_name = str(payload.get("product_name") or request_type or "换花")
    variant_name = str(payload.get("variant_name") or "")
    unit = str(payload.get("unit") or "盆")
    location_text = str(payload.get("location_text") or "")
    sequence = (db.scalar(select(func.count()).select_from(BusinessOrder)) or 0) + 1
    order_no = str(payload.get("order_no") or "").strip() or source_no("SJHH", f"{date.today().strftime('%Y%m%d')}{sequence:04d}")
    while db.scalar(select(BusinessOrder).where(BusinessOrder.order_no == order_no)):
        sequence += 1
        order_no = source_no("SJHH", f"{date.today().strftime('%Y%m%d')}{sequence:04d}")
    order = BusinessOrder(
        order_no=order_no,
        order_type="换花订单",
        project_id=project.id,
        project_name=project.name,
        customer_name=project.name,
        requester=user.display_name or user.username,
        contact_phone=str(payload.get("contact_phone") or ""),
        order_date=date.today(),
        expected_date=parse_date(payload.get("expected_date")),
        priority=str(payload.get("priority") or "普通"),
        need_purchase=bool(payload.get("need_purchase") if payload.get("need_purchase") is not None else True),
        need_delivery=bool(payload.get("need_delivery") if payload.get("need_delivery") is not None else True),
        status="待处理",
        notes=str(payload.get("notes") or ""),
    )
    db.add(order)
    db.flush()
    item = BusinessOrderItem(
        order_id=order.id,
        product_name=product_name,
        variant_name=variant_name,
        location_text=location_text,
        quantity=quantity,
        unit=unit,
        unit_price=0,
        amount=0,
        notes=f"手机端{request_type}：{payload.get('reason') or ''}".strip("："),
    )
    db.add(item)
    db.flush()
    ensure_order_approval(order, db)
    db.commit()
    db.refresh(order)
    return serialize_order(order, db)


@router.put("/{order_id}")
def update_order(
    order_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_module(user, "orders")
    order = db.get(BusinessOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status in {"已完成", "已取消"}:
        raise HTTPException(status_code=400, detail="已完成或已取消订单不能修改")
    if not can_access_project(user, order.project_id, db):
        raise HTTPException(status_code=403, detail="无权修改该订单")
    if "order_no" in payload and payload["order_no"] != order.order_no:
        if db.scalar(select(BusinessOrder).where(BusinessOrder.order_no == payload["order_no"], BusinessOrder.id != order_id)):
            raise HTTPException(status_code=409, detail="订单号已存在")
        order.order_no = str(payload["order_no"])
    for key in ["project_name", "customer_name", "requester", "contact_phone", "priority", "status", "notes"]:
        if key in payload:
            setattr(order, key, str(payload.get(key) or ""))
    if "order_type" in payload:
        order.order_type = TYPE_MAP.get(str(payload.get("order_type") or ""), str(payload.get("order_type") or order.order_type))
    if "project_id" in payload:
        new_project_id = int(payload["project_id"]) if payload.get("project_id") else None
        if not can_access_project(user, new_project_id, db):
            raise HTTPException(status_code=403, detail="无权将订单改到该项目")
        order.project_id = new_project_id
    if "order_date" in payload:
        order.order_date = parse_date(payload.get("order_date"))
    if "expected_date" in payload:
        order.expected_date = parse_date(payload.get("expected_date"))
    if "need_purchase" in payload:
        order.need_purchase = bool(payload.get("need_purchase"))
    if "need_delivery" in payload:
        order.need_delivery = bool(payload.get("need_delivery"))
    if "items" in payload:
        replace_items(order, payload.get("items") or [], db)
        db.flush()
    ensure_order_approval(order, db)
    sync_order_status_from_flow(order, db)
    db.commit()
    db.refresh(order)
    return serialize_order(order, db)


@router.post("/{order_id}/status")
def change_order_status(
    order_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_module(user, "orders")
    order = db.get(BusinessOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not can_access_project(user, order.project_id, db):
        raise HTTPException(status_code=403, detail="无权修改该订单状态")
    status = str(payload.get("status") or "").strip()
    if not status:
        raise HTTPException(status_code=400, detail="请填写状态")
    previous_status = order.status
    order.status = status
    if status == "已完成" and previous_status != "已完成":
        apply_project_plant_linkage(order, db)
    db.commit()
    db.refresh(order)
    return serialize_order(order, db)


@router.post("/{order_id}/create-purchase")
def create_purchase_from_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_module(user, "purchase_inventory")
    order = db.get(BusinessOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not can_access_project(user, order.project_id, db):
        raise HTTPException(status_code=403, detail="无权操作该订单")
    if order.status == "待审批":
        raise HTTPException(status_code=400, detail="订单正在审批中，审批通过后才能生成采购单")
    if order.status == "已驳回":
        raise HTTPException(status_code=400, detail="订单审批已驳回，不能生成采购单")
    generated_no = source_no("CG", order.order_no)
    existing = db.scalar(select(PurchaseOrder).where(PurchaseOrder.order_no == generated_no))
    if existing:
        return {"status": "exists", "purchase_order_id": existing.id, "purchase_order_no": existing.order_no}

    items = db.scalars(select(BusinessOrderItem).where(BusinessOrderItem.order_id == order.id).order_by(BusinessOrderItem.id)).all()
    product_items = [item for item in items if item.product_id]
    if not product_items:
        raise HTTPException(status_code=400, detail="订单没有可采购的商品明细")
    if order_items_all_in_stock(product_items, db):
        order.need_purchase = False
        order.status = "待配送" if order.need_delivery else "已完成"
        db.commit()
        db.refresh(order)
        return {"status": "stock_available", "purchase_order_id": None, "purchase_order_no": "", "message": "仓库库存充足，已进入待配送"}

    purchase = PurchaseOrder(
        order_no=generated_no,
        supplier="",
        purchaser=default_purchaser(db, user),
        purchase_date=order.order_date,
        delivery_method="入库" if order.need_delivery else "供应商直送",
        status="待采购",
        notes=f"由订单 {order.order_no} 生成；项目/用途：{order.project_name}",
    )
    db.add(purchase)
    db.flush()
    for source_item in product_items:
        product = db.get(Product, source_item.product_id)
        is_bundle_purchase = bool(product and product.package_conversion_enabled)
        purchase_variant_id = None if is_bundle_purchase else source_item.variant_id
        purchase_variant_name = "成套采购" if is_bundle_purchase else source_item.variant_name
        purchase_unit = (product.purchase_unit or product.unit) if is_bundle_purchase and product else item_unit(source_item, db)
        purchase_price = float(product.reference_purchase_price or 0) if is_bundle_purchase and product else cost_price(source_item, db)
        source_note_parts = [source_item.location_text or source_item.notes or ""]
        if is_bundle_purchase and source_item.variant_name:
            source_note_parts.append(f"项目需要型号：{source_item.variant_name}；采购按整套执行")
        purchase_item = PurchaseOrderItem(
            order_id=purchase.id,
            product_id=int(source_item.product_id),
            variant_id=purchase_variant_id,
            product_name=source_item.product_name,
            variant_name=purchase_variant_name,
            quantity=source_item.quantity,
            received_quantity=0,
            unit=purchase_unit,
            unit_price=purchase_price,
            notes="；".join([part for part in source_note_parts if part]),
        )
        db.add(purchase_item)
    order.need_purchase = True
    sync_order_status_from_flow(order, db)
    db.commit()
    db.refresh(purchase)
    return {"status": "created", "purchase_order_id": purchase.id, "purchase_order_no": purchase.order_no}


@router.post("/{order_id}/create-outbound")
def create_outbound_from_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_module(user, "purchase_inventory")
    order = db.get(BusinessOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not can_access_project(user, order.project_id, db):
        raise HTTPException(status_code=403, detail="无权操作该订单")
    if order.status == "待审批":
        raise HTTPException(status_code=400, detail="订单正在审批中，审批通过后才能生成出库单")
    if order.status == "已驳回":
        raise HTTPException(status_code=400, detail="订单审批已驳回，不能生成出库单")
    generated_no = source_no("CK", order.order_no)
    existing = db.scalar(select(OutboundOrder).where(OutboundOrder.order_no == generated_no))
    if existing:
        return {"status": "exists", "outbound_order_id": existing.id, "outbound_order_no": existing.order_no}

    items = db.scalars(select(BusinessOrderItem).where(BusinessOrderItem.order_id == order.id).order_by(BusinessOrderItem.id)).all()
    product_items = [item for item in items if item.product_id]
    if not product_items:
        raise HTTPException(status_code=400, detail="订单没有可出库的商品明细")

    outbound = OutboundOrder(
        order_no=generated_no,
        outbound_type=order.order_type.replace("订单", "出库"),
        project_name=order.project_name,
        handler=order.requester or user.display_name or user.username,
        outbound_date=order.expected_date or order.order_date,
        status="待配送",
        notes=f"由订单 {order.order_no} 生成；客户：{order.customer_name}",
    )
    db.add(outbound)
    db.flush()
    for source_item in product_items:
        outbound_item = OutboundOrderItem(
            order_id=outbound.id,
            product_id=int(source_item.product_id),
            variant_id=source_item.variant_id,
            product_name=source_item.product_name,
            variant_name=source_item.variant_name,
            quantity=source_item.quantity,
            unit=item_unit(source_item, db),
            unit_price=cost_price(source_item, db),
            notes=source_item.location_text or source_item.notes,
        )
        db.add(outbound_item)
    order.need_delivery = True
    sync_order_status_from_flow(order, db)
    db.commit()
    db.refresh(outbound)
    return {"status": "created", "outbound_order_id": outbound.id, "outbound_order_no": outbound.order_no}
