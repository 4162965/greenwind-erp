from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import BusinessOrder, BusinessOrderItem, Employee, InventoryMovement, OutboundOrder, OutboundOrderItem, Product, ProductVariant, Project, PurchaseOrder, ScheduleTask, User, Vehicle
from ..permissions import can_access_project, employee_for_user
from .orders import apply_project_plant_linkage
from ..schemas import (
    ScheduleTaskCreate,
    ScheduleTaskRead,
    ScheduleTaskUpdate,
    VehicleCreate,
    VehicleRead,
    VehicleUpdate,
)


vehicle_router = APIRouter(prefix="/api/v1/vehicles", tags=["vehicles"])
schedule_router = APIRouter(prefix="/api/v1/schedules", tags=["schedules"])


def source_no(prefix: str, source: str) -> str:
    return f"{prefix}-{source}"[:64]


def format_quantity(value: float) -> str:
    return str(int(value)) if float(value or 0).is_integer() else str(round(float(value or 0), 2)).rstrip("0").rstrip(".")


def order_item_summary(items: list[BusinessOrderItem]) -> str:
    parts = []
    for item in items:
        name = item.product_name or "事项"
        variant = f" {item.variant_name}" if item.variant_name else ""
        location = f"（{item.location_text}）" if item.location_text else ""
        parts.append(f"{name}{variant}{location} × {format_quantity(item.quantity)}{item.unit}")
    return "；".join(parts)


def outbound_item_summary(items: list[OutboundOrderItem]) -> str:
    parts = []
    for item in items:
        variant = f" {item.variant_name}" if item.variant_name else ""
        note = f"（{item.notes}）" if item.notes else ""
        parts.append(f"{item.product_name}{variant}{note} × {format_quantity(item.quantity)}{item.unit}")
    return "；".join(parts)


def employee_name(employee_id: int | None, db: Session) -> str:
    if not employee_id:
        return ""
    employee = db.get(Employee, employee_id)
    return employee.name if employee else ""


def assistant_names(assistant_ids: str, db: Session) -> str:
    ids = parse_assistant_ids(assistant_ids)
    if not ids:
        return ""
    employees = db.scalars(select(Employee).where(Employee.id.in_(ids))).all()
    by_id = {employee.id: employee.name for employee in employees}
    return "、".join(by_id.get(employee_id, "") for employee_id in ids if by_id.get(employee_id))


def parse_assistant_ids(assistant_ids: str) -> list[int]:
    ids = []
    for value in (assistant_ids or "").split(","):
        value = value.strip()
        if value.isdigit():
            ids.append(int(value))
    return ids


def serialize_schedule(task: ScheduleTask, db: Session) -> ScheduleTaskRead:
    data = ScheduleTaskRead.model_validate(task)
    data.driver_name = employee_name(task.driver_id, db)
    data.assistant_names = assistant_names(task.assistant_ids, db)
    vehicle = db.get(Vehicle, task.vehicle_id) if task.vehicle_id else None
    data.vehicle_plate_no = vehicle.plate_no if vehicle else ""
    return data


def vehicle_reminder_items(vehicle: Vehicle) -> tuple[str, list[str]]:
    today = date.today()
    reminder_days = vehicle.reminder_days or 0
    upcoming_before = today + timedelta(days=reminder_days)
    items: list[str] = []
    has_expired = False
    has_upcoming = False
    checks = [
        ("保险", vehicle.insurance_expiry),
        ("年检", vehicle.inspection_expiry),
        ("保养", vehicle.maintenance_due_date),
    ]
    for label, due_date in checks:
        if not due_date:
            continue
        if due_date < today:
            items.append(f"{label}已过期（{due_date.isoformat()}）")
            has_expired = True
        elif due_date <= upcoming_before:
            items.append(f"{label}即将到期（{due_date.isoformat()}）")
            has_upcoming = True
    if has_expired:
        return "已过期", items
    if has_upcoming:
        return "即将到期", items
    return "正常", items


def serialize_vehicle(vehicle: Vehicle) -> VehicleRead:
    data = VehicleRead.model_validate(vehicle)
    data.reminder_status, data.reminder_items = vehicle_reminder_items(vehicle)
    return data


def product_stock(product: Product, db: Session) -> float:
    variants = db.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id)).all()
    if variants:
        return float(sum(float(variant.stock or 0) for variant in variants))
    return float(product.stock or 0)


def apply_delivery_stock(order: BusinessOrder, task: ScheduleTask, db: Session):
    if db.scalar(
        select(InventoryMovement.id).where(
            InventoryMovement.source_type == "配送完成",
            InventoryMovement.source_no == order.order_no,
        )
    ):
        return
    items = db.scalars(select(BusinessOrderItem).where(BusinessOrderItem.order_id == order.id).order_by(BusinessOrderItem.id)).all()
    for item in items:
        if not item.product_id:
            continue
        product = db.get(Product, item.product_id)
        if not product:
            continue
        quantity = float(item.quantity or 0)
        if quantity <= 0:
            continue
        unit_price = float(item.unit_price or 0)
        if item.variant_id:
            variant = db.get(ProductVariant, item.variant_id)
            if not variant:
                continue
            before_stock = float(variant.stock or 0)
            variant.stock = max(0, before_stock - quantity)
            if not product.package_conversion_enabled:
                product.stock = int(product_stock(product, db))
            after_stock = float(variant.stock or 0)
            unit = variant.unit or item.unit or product.unit
            variant_name = item.variant_name or variant.specification or variant.code
        else:
            before_stock = float(product.stock or 0)
            product.stock = int(max(0, before_stock - quantity))
            after_stock = float(product.stock or 0)
            unit = item.unit or product.unit or product.purchase_unit
            variant_name = item.variant_name or ""
        db.add(
            InventoryMovement(
                product_id=product.id,
                variant_id=item.variant_id,
                product_name=item.product_name or product.name,
                variant_name=variant_name,
                movement_type="配送带货",
                direction="出库",
                quantity=quantity,
                before_stock=before_stock,
                after_stock=after_stock,
                unit=unit,
                unit_price=unit_price,
                total_amount=quantity * unit_price,
                source_type="配送完成",
                source_no=order.order_no,
                operator=task.task_no,
                notes=f"配送任务 {task.task_no} 完成后自动扣减库存",
            )
        )


def ensure_vehicle(vehicle_id: int | None, db: Session):
    if vehicle_id and not db.get(Vehicle, vehicle_id):
        raise HTTPException(status_code=400, detail="车辆不存在")


def ensure_employee(employee_id: int | None, db: Session):
    if employee_id and not db.get(Employee, employee_id):
        raise HTTPException(status_code=400, detail="员工不存在")


def ensure_assistants(assistant_ids: str | None, db: Session):
    for value in (assistant_ids or "").split(","):
        value = value.strip()
        if value and (not value.isdigit() or not db.get(Employee, int(value))):
            raise HTTPException(status_code=400, detail="跟车人员不存在")


def sync_source_progress(task: ScheduleTask, status_text: str, db: Session):
    order_status_map = {
        "配送中": "配送中",
        "已出发": "配送中",
        "已送达": "已送达",
        "已完成": "已完成",
    }
    mapped_status = order_status_map.get(status_text)
    if not mapped_status:
        return

    source_type = task.source_type or ""
    source_no = task.source_no or ""
    if source_type == "订单":
        order = db.scalar(select(BusinessOrder).where(BusinessOrder.order_no == source_no))
        if order and order.status not in {"已取消", "已驳回"}:
            order.status = mapped_status
            if mapped_status == "已完成":
                apply_delivery_stock(order, task, db)
                apply_project_plant_linkage(order, db)
        return

    if source_type == "出库单":
        outbound = db.scalar(select(OutboundOrder).where(OutboundOrder.order_no == source_no))
        if outbound and outbound.status not in {"已取消", "作废"}:
            outbound.status = mapped_status
        related_order_no = source_no[3:] if source_no.startswith("CK-") else ""
        if related_order_no:
            order = db.scalar(select(BusinessOrder).where(BusinessOrder.order_no == related_order_no))
            if order and order.status not in {"已取消", "已驳回"}:
                order.status = mapped_status
                if mapped_status == "已完成":
                    apply_project_plant_linkage(order, db)


@vehicle_router.get("")
def list_vehicles(
    keyword: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    filters = []
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(Vehicle.plate_no.like(pattern), Vehicle.vehicle_type.like(pattern), Vehicle.driver_name.like(pattern)))
    items = db.scalars(select(Vehicle).where(*filters).order_by(Vehicle.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(Vehicle).where(*filters)) or 0
    return {"items": [serialize_vehicle(item) for item in items], "total": total}


@vehicle_router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    payload: VehicleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    if db.scalar(select(Vehicle).where(Vehicle.plate_no == payload.plate_no)):
        raise HTTPException(status_code=409, detail="车牌号已存在")
    vehicle = Vehicle(**payload.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return serialize_vehicle(vehicle)


@vehicle_router.put("/{vehicle_id}", response_model=VehicleRead)
def update_vehicle(
    vehicle_id: int,
    payload: VehicleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="车辆不存在")
    values = payload.model_dump(exclude_unset=True)
    if "plate_no" in values and values["plate_no"] != vehicle.plate_no:
        if db.scalar(select(Vehicle).where(Vehicle.plate_no == values["plate_no"], Vehicle.id != vehicle_id)):
            raise HTTPException(status_code=409, detail="车牌号已存在")
    for key, value in values.items():
        setattr(vehicle, key, value)
    db.commit()
    db.refresh(vehicle)
    return serialize_vehicle(vehicle)


@vehicle_router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="车辆不存在")
    db.delete(vehicle)
    db.commit()


@schedule_router.get("")
def list_schedules(
    schedule_date: date | None = Query(default=None),
    keyword: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    filters = []
    if schedule_date:
        filters.append(ScheduleTask.schedule_date == schedule_date)
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(
            or_(
                ScheduleTask.task_no.like(pattern),
                ScheduleTask.project_name.like(pattern),
                ScheduleTask.source_no.like(pattern),
                ScheduleTask.item_summary.like(pattern),
            )
        )
    items = db.scalars(select(ScheduleTask).where(*filters).order_by(ScheduleTask.schedule_date.desc(), ScheduleTask.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(ScheduleTask).where(*filters)) or 0
    return {"items": [serialize_schedule(item, db) for item in items], "total": total}


@schedule_router.get("/my")
def list_my_schedules(
    schedule_date: date | None = Query(default=None),
    keyword: str = Query(default="", max_length=100),
    include_done: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    employee = employee_for_user(user, db)
    if not employee:
        return {"items": [], "total": 0}
    filters = [ScheduleTask.status != "待发布", ScheduleTask.status != "已取消"]
    if not include_done:
        filters.append(ScheduleTask.status != "已完成")
    if schedule_date:
        filters.append(ScheduleTask.schedule_date == schedule_date)
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(
            or_(
                ScheduleTask.task_no.like(pattern),
                ScheduleTask.project_name.like(pattern),
                ScheduleTask.source_no.like(pattern),
                ScheduleTask.item_summary.like(pattern),
            )
        )
    tasks = db.scalars(select(ScheduleTask).where(*filters).order_by(ScheduleTask.schedule_date.desc(), ScheduleTask.id.desc())).all()
    items = [
        task
        for task in tasks
        if task.driver_id == employee.id or employee.id in parse_assistant_ids(task.assistant_ids)
    ]
    return {"items": [serialize_schedule(item, db) for item in items], "total": len(items)}


@schedule_router.post("", response_model=ScheduleTaskRead, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: ScheduleTaskCreate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    if db.scalar(select(ScheduleTask).where(ScheduleTask.task_no == payload.task_no)):
        raise HTTPException(status_code=409, detail="安排单号已存在")
    ensure_employee(payload.driver_id, db)
    ensure_assistants(payload.assistant_ids, db)
    ensure_vehicle(payload.vehicle_id, db)
    task = ScheduleTask(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return serialize_schedule(task, db)


@schedule_router.post("/from-order/{order_id}")
def create_schedule_from_order(
    order_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    order = db.get(BusinessOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not can_access_project(user, order.project_id, db):
        raise HTTPException(status_code=403, detail="无权操作该订单")
    if order.status == "待审批":
        raise HTTPException(status_code=400, detail="订单正在审批中，审批通过后才能生成每日安排")
    if order.status == "已驳回":
        raise HTTPException(status_code=400, detail="订单审批已驳回，不能生成每日安排")
    if order.need_purchase:
        purchase = db.scalar(select(PurchaseOrder).where(PurchaseOrder.order_no == source_no("CG", order.order_no)))
        if not purchase:
            raise HTTPException(status_code=400, detail="该订单需要采购，请先生成采购任务")
        if purchase.status != "已入库":
            raise HTTPException(status_code=400, detail="采购还没有入库，不能派配送")
    generated_no = source_no("RC", order.order_no)
    existing = db.scalar(select(ScheduleTask).where(ScheduleTask.task_no == generated_no))
    if existing:
        return {"status": "exists", "schedule_id": existing.id, "task_no": existing.task_no}
    items = db.scalars(select(BusinessOrderItem).where(BusinessOrderItem.order_id == order.id).order_by(BusinessOrderItem.id)).all()
    if not items:
        raise HTTPException(status_code=400, detail="订单没有可生成安排的明细")
    project = db.get(Project, order.project_id) if order.project_id else None
    task_type = "配送"
    if "换花" in order.order_type:
        task_type = "换花"
    elif "撤花" in order.order_type:
        task_type = "撤花"
    elif "养护" in order.order_type:
        task_type = "修剪打药"
    payload = payload or {}
    schedule_date = payload.get("schedule_date") or order.expected_date or order.order_date or date.today()
    if isinstance(schedule_date, str):
        schedule_date = date.fromisoformat(schedule_date)
    driver_id = int(payload["driver_id"]) if payload.get("driver_id") else None
    vehicle_id = int(payload["vehicle_id"]) if payload.get("vehicle_id") else None
    assistant_ids = str(payload.get("assistant_ids") or "")
    ensure_employee(driver_id, db)
    ensure_assistants(assistant_ids, db)
    ensure_vehicle(vehicle_id, db)
    task = ScheduleTask(
        task_no=generated_no,
        schedule_date=schedule_date,
        task_type=task_type,
        source_type="订单",
        source_no=order.order_no,
        project_name=order.project_name,
        address=project.address if project else "",
        driver_id=driver_id,
        assistant_ids=assistant_ids,
        vehicle_id=vehicle_id,
        planned_start=str(payload.get("planned_start") or ""),
        planned_end=str(payload.get("planned_end") or ""),
        item_summary=order_item_summary(items),
        status="已发布",
        notes=f"由订单 {order.order_no} 生成；联系人：{order.contact_phone or order.customer_name}",
    )
    db.add(task)
    order.need_delivery = True
    order.status = "待配送"
    db.commit()
    db.refresh(task)
    return {"status": "created", "schedule_id": task.id, "task_no": task.task_no}


@schedule_router.post("/from-outbound/{order_id}")
def create_schedule_from_outbound(
    order_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    order = db.get(OutboundOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="出库单不存在")
    generated_no = source_no("RC", order.order_no)
    existing = db.scalar(select(ScheduleTask).where(ScheduleTask.task_no == generated_no))
    if existing:
        return {"status": "exists", "schedule_id": existing.id, "task_no": existing.task_no}
    items = db.scalars(select(OutboundOrderItem).where(OutboundOrderItem.order_id == order.id).order_by(OutboundOrderItem.id)).all()
    if not items:
        raise HTTPException(status_code=400, detail="出库单没有可生成安排的明细")
    payload = payload or {}
    schedule_date = payload.get("schedule_date") or order.outbound_date or date.today()
    if isinstance(schedule_date, str):
        schedule_date = date.fromisoformat(schedule_date)
    driver_id = int(payload["driver_id"]) if payload.get("driver_id") else None
    vehicle_id = int(payload["vehicle_id"]) if payload.get("vehicle_id") else None
    assistant_ids = str(payload.get("assistant_ids") or "")
    ensure_employee(driver_id, db)
    ensure_assistants(assistant_ids, db)
    ensure_vehicle(vehicle_id, db)
    task = ScheduleTask(
        task_no=generated_no,
        schedule_date=schedule_date,
        task_type="配送",
        source_type="出库单",
        source_no=order.order_no,
        project_name=order.project_name,
        driver_id=driver_id,
        assistant_ids=assistant_ids,
        vehicle_id=vehicle_id,
        planned_start=str(payload.get("planned_start") or ""),
        planned_end=str(payload.get("planned_end") or ""),
        item_summary=outbound_item_summary(items),
        status="已发布",
        notes=str(payload.get("notes") or f"由出库单 {order.order_no} 生成；经办人：{order.handler}"),
    )
    db.add(task)
    related_order_no = order.order_no[3:] if str(order.order_no or "").startswith("CK-") else ""
    if related_order_no:
        business = db.scalar(select(BusinessOrder).where(BusinessOrder.order_no == related_order_no))
        if business and business.status not in {"已完成", "已取消", "已驳回"}:
            business.status = "待配送"
    db.commit()
    db.refresh(task)
    return {"status": "created", "schedule_id": task.id, "task_no": task.task_no}


@schedule_router.put("/{task_id}", response_model=ScheduleTaskRead)
def update_schedule(
    task_id: int,
    payload: ScheduleTaskUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    task = db.get(ScheduleTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="安排不存在")
    values = payload.model_dump(exclude_unset=True)
    if "task_no" in values and values["task_no"] != task.task_no:
        if db.scalar(select(ScheduleTask).where(ScheduleTask.task_no == values["task_no"], ScheduleTask.id != task_id)):
            raise HTTPException(status_code=409, detail="安排单号已存在")
    ensure_employee(values.get("driver_id"), db)
    ensure_assistants(values.get("assistant_ids"), db)
    ensure_vehicle(values.get("vehicle_id"), db)
    for key, value in values.items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return serialize_schedule(task, db)


@schedule_router.post("/{task_id}/status", response_model=ScheduleTaskRead)
def change_schedule_status(
    task_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    task = db.get(ScheduleTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="安排不存在")
    status_text = str(payload.get("status") or "").strip()
    if not status_text:
        raise HTTPException(status_code=400, detail="请填写状态")
    task.status = status_text
    sync_source_progress(task, status_text, db)
    db.commit()
    db.refresh(task)
    return serialize_schedule(task, db)


@schedule_router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    task_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    task = db.get(ScheduleTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="安排不存在")
    db.delete(task)
    db.commit()
