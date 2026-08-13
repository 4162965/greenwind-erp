from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import (
    ApprovalRequest,
    BusinessOrder,
    Contract,
    Employee,
    MaintenancePlan,
    MaintenanceRecord,
    OutboundOrder,
    PurchaseOrder,
    ReceivableRecord,
    ReceiptRecord,
    ScheduleTask,
    User,
    Vehicle,
)
from ..permissions import employee_for_user, has_full_access


router = APIRouter(prefix="/api/v1/dashboard", tags=["仪表盘"])


def money(value: float | int | None) -> float:
    return round(float(value or 0), 2)


def count_where(db: Session, model, *conditions) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0)


def due_label(due_date: date | None) -> str:
    if not due_date:
        return ""
    today = date.today()
    delta = (due_date - today).days
    if delta < 0:
        return f"已过期 {abs(delta)} 天"
    if delta == 0:
        return "今天到期"
    return f"{delta} 天后"


def vehicle_reminder_status(vehicle: Vehicle) -> tuple[str, list[str]]:
    today = date.today()
    upcoming_before = today + timedelta(days=vehicle.reminder_days or 0)
    items: list[str] = []
    expired = False
    upcoming = False
    for label, due_date in [
        ("保险", vehicle.insurance_expiry),
        ("年检", vehicle.inspection_expiry),
        ("保养", vehicle.maintenance_due_date),
    ]:
        if not due_date:
            continue
        if due_date < today:
            expired = True
            items.append(f"{label}已过期")
        elif due_date <= upcoming_before:
            upcoming = True
            items.append(f"{label}即将到期")
    if expired:
        return "已过期", items
    if upcoming:
        return "即将到期", items
    return "正常", items


def date_text(value: date | None) -> str:
    return value.isoformat() if value else ""


def user_role_text(user: User) -> str:
    return f"{user.role or ''},{user.module_permissions or ''}"


def assistant_id_set(value: str) -> set[int]:
    result = set()
    for part in (value or "").replace("，", ",").split(","):
        part = part.strip()
        if part.isdigit():
            result.add(int(part))
    return result


@router.get("/my-workbench")
def my_workbench(db: Session = Depends(get_db), user: User = Depends(current_user)):
    employee = employee_for_user(user, db)
    employee_id = employee.id if employee else None
    role_text = user_role_text(user)
    is_full = has_full_access(user)
    today = date.today()
    week_end = today + timedelta(days=7)

    purchase_filters = [PurchaseOrder.status.in_(["待采购", "待入库"])]
    if not is_full:
        names = [user.display_name, user.username]
        if employee:
            names.extend([employee.name, employee.phone])
        purchase_filters.append(PurchaseOrder.purchaser.in_([item for item in names if item]))
    purchase_rows = db.scalars(
        select(PurchaseOrder).where(*purchase_filters).order_by(PurchaseOrder.purchase_date.asc(), PurchaseOrder.id.desc()).limit(12)
    ).all()

    inbound_filters = [PurchaseOrder.status == "待入库"]
    inbound_rows = db.scalars(
        select(PurchaseOrder).where(*inbound_filters).order_by(PurchaseOrder.purchase_date.asc(), PurchaseOrder.id.desc()).limit(12)
    ).all()
    if not is_full and "仓" not in role_text and "库" not in role_text:
        inbound_rows = []

    schedule_query = (
        select(ScheduleTask)
        .where(ScheduleTask.schedule_date >= today, ScheduleTask.schedule_date <= week_end, ScheduleTask.status != "已取消")
        .order_by(ScheduleTask.schedule_date.asc(), ScheduleTask.planned_start.asc(), ScheduleTask.id.desc())
    )
    schedule_candidates = db.scalars(schedule_query).all()
    if is_full or not employee_id:
        schedule_rows = schedule_candidates[:12]
    else:
        schedule_rows = [
            row for row in schedule_candidates
            if row.driver_id == employee_id or employee_id in assistant_id_set(row.assistant_ids)
        ][:12]

    maintenance_filters = [
        MaintenancePlan.status == "启用",
        or_(MaintenancePlan.next_due_date == None, MaintenancePlan.next_due_date <= week_end),
    ]
    if employee_id and not is_full:
        maintenance_filters.append(MaintenancePlan.maintainer_id == employee_id)
    maintenance_plans = db.scalars(
        select(MaintenancePlan).where(*maintenance_filters).order_by(MaintenancePlan.next_due_date.asc(), MaintenancePlan.id.desc()).limit(12)
    ).all()

    recent_records_filters = []
    if employee_id and not is_full:
        recent_records_filters.append(MaintenanceRecord.maintainer_id == employee_id)
    recent_records = db.scalars(
        select(MaintenanceRecord).where(*recent_records_filters).order_by(MaintenanceRecord.service_date.desc(), MaintenanceRecord.id.desc()).limit(8)
    ).all()

    todo_count = len(purchase_rows) + len(inbound_rows) + len(schedule_rows) + len(maintenance_plans)
    role_cards = [
        {"label": "采购任务", "value": len(purchase_rows), "path": "/module/purchase/my", "hint": "待采购/待入库"},
        {"label": "入库任务", "value": len(inbound_rows), "path": "/module/inventory/inbound", "hint": "仓管待处理"},
        {"label": "配送/日程", "value": len(schedule_rows), "path": "/module/schedule/my", "hint": "未来7天"},
        {"label": "养护计划", "value": len(maintenance_plans), "path": "/module/maintenance/manage", "hint": "即将到期"},
    ]
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "employee_id": employee_id,
            "employee_name": employee.name if employee else "",
            "department": employee.department if employee else "",
            "position": employee.position if employee else "",
        },
        "summary": {"todo_count": todo_count, "today": today.isoformat(), "week_end": week_end.isoformat()},
        "role_cards": role_cards,
        "purchase_tasks": [
            {
                "id": row.id,
                "order_no": row.order_no,
                "supplier": row.supplier,
                "purchaser": row.purchaser,
                "purchase_date": date_text(row.purchase_date),
                "status": row.status,
                "amount": money(row.freight_fee + row.hll_fee),
                "notes": row.notes,
                "path": "/module/purchase/my",
            }
            for row in purchase_rows
        ],
        "inbound_tasks": [
            {
                "id": row.id,
                "order_no": row.order_no,
                "supplier": row.supplier,
                "purchaser": row.purchaser,
                "purchase_date": date_text(row.purchase_date),
                "status": row.status,
                "notes": row.notes,
                "path": "/module/inventory/inbound",
            }
            for row in inbound_rows
        ],
        "schedule_tasks": [
            {
                "id": row.id,
                "task_no": row.task_no,
                "schedule_date": date_text(row.schedule_date),
                "planned_start": row.planned_start,
                "planned_end": row.planned_end,
                "task_type": row.task_type,
                "project_name": row.project_name,
                "address": row.address,
                "item_summary": row.item_summary,
                "status": row.status,
                "path": "/module/schedule/my",
            }
            for row in schedule_rows
        ],
        "maintenance_tasks": [
            {
                "id": row.id,
                "plan_no": row.plan_no,
                "project_name": row.project_name,
                "area_description": row.area_description,
                "service_content": row.service_content,
                "next_due_date": date_text(row.next_due_date),
                "status": row.status,
                "path": "/module/maintenance/manage",
            }
            for row in maintenance_plans
        ],
        "maintenance_records": [
            {
                "id": row.id,
                "record_no": row.record_no,
                "project_name": row.project_name,
                "service_date": date_text(row.service_date),
                "area_description": row.area_description,
                "site_issue": row.site_issue,
                "handle_result": row.handle_result,
                "status": row.status,
            }
            for row in recent_records
        ],
    }


@router.get("/summary")
def summary(db: Session = Depends(get_db), _: User = Depends(current_user)):
    today = date.today()
    month_start = today.replace(day=1)
    trend_start = today - timedelta(days=6)
    tomorrow = today + timedelta(days=1)
    contract_alert_until = today + timedelta(days=45)

    pending_purchase = count_where(db, PurchaseOrder, PurchaseOrder.status.in_(["待采购", "待入库"]))
    pending_outbound = count_where(db, OutboundOrder, OutboundOrder.status.in_(["待出库", "已出库", "配送中"]))
    pending_approval = count_where(db, ApprovalRequest, ApprovalRequest.status == "待审批")
    month_orders = count_where(db, BusinessOrder, BusinessOrder.order_date >= month_start)
    month_receipts = money(db.scalar(select(func.coalesce(func.sum(ReceiptRecord.amount), 0)).where(ReceiptRecord.receipt_date >= month_start)))
    receivable_total = money(db.scalar(select(func.coalesce(func.sum(ReceivableRecord.amount), 0)).where(ReceivableRecord.status != "作废")))
    received_total = money(db.scalar(select(func.coalesce(func.sum(ReceivableRecord.received_amount), 0)).where(ReceivableRecord.status != "作废")))
    unreceived_total = money(receivable_total - received_total)
    overdue_receivable = money(
        db.scalar(
            select(func.coalesce(func.sum(ReceivableRecord.amount - ReceivableRecord.received_amount), 0)).where(
                ReceivableRecord.status != "已收款",
                ReceivableRecord.status != "作废",
                ReceivableRecord.due_date < today,
            )
        )
    )
    expiring_contracts = db.scalars(
        select(Contract)
        .where(Contract.status == "生效", Contract.end_date >= today, Contract.end_date <= contract_alert_until)
        .order_by(Contract.end_date.asc())
    ).all()
    vehicle_alerts = []
    for vehicle in db.scalars(select(Vehicle).order_by(Vehicle.id.desc())).all():
        status, items = vehicle_reminder_status(vehicle)
        if status != "正常":
            vehicle_alerts.append({"plate_no": vehicle.plate_no, "status": status, "items": "、".join(items), "reminder_to": vehicle.reminder_to})

    order_rows = db.scalars(select(BusinessOrder).where(BusinessOrder.order_date >= trend_start)).all()
    labels = [(trend_start + timedelta(days=i)).strftime("%m-%d") for i in range(7)]
    sales = []
    for i in range(7):
        day = trend_start + timedelta(days=i)
        sales.append(len([row for row in order_rows if row.order_date == day]))

    order_types = ["租摆订单", "销售订单", "换花单", "撤花单", "养护工程订单", "配送订单"]
    composition = []
    total_orders = count_where(db, BusinessOrder)
    for order_type in order_types:
        composition.append({"label": order_type, "value": count_where(db, BusinessOrder, BusinessOrder.order_type == order_type)})

    todo_candidates = []
    for row in db.scalars(select(ApprovalRequest).where(ApprovalRequest.status == "待审批").order_by(ApprovalRequest.created_at.desc()).limit(5)).all():
        todo_candidates.append({"title": f"{row.source_no or row.request_no} 待审批", "type": row.approval_type, "time": "待处理", "path": "/module/workflow/progress"})
    for row in db.scalars(select(PurchaseOrder).where(PurchaseOrder.status.in_(["待采购", "待入库"])).order_by(PurchaseOrder.id.desc()).limit(5)).all():
        todo_candidates.append({"title": f"{row.order_no} {row.status}", "type": "采购", "time": row.purchase_date.isoformat() if row.purchase_date else "待处理", "path": "/module/purchase/list"})
    for row in db.scalars(select(ReceivableRecord).where(ReceivableRecord.status != "已收款", ReceivableRecord.status != "作废").order_by(ReceivableRecord.due_date.asc()).limit(5)).all():
        todo_candidates.append({"title": f"{row.receivable_no} 未收款 ¥{money(float(row.amount or 0) - float(row.received_amount or 0))}", "type": "应收", "time": due_label(row.due_date), "path": "/module/finance/receivable"})
    for row in expiring_contracts[:5]:
        todo_candidates.append({"title": f"{row.contract_no} 合同即将到期", "type": "合同", "time": due_label(row.end_date), "path": "/module/finance/contract"})

    today_schedules = db.scalars(
        select(ScheduleTask)
        .where(ScheduleTask.schedule_date >= today, ScheduleTask.schedule_date <= tomorrow, ScheduleTask.status != "已取消")
        .order_by(ScheduleTask.schedule_date.asc(), ScheduleTask.planned_start.asc())
        .limit(8)
    ).all()

    return {
        "metrics": [
            {"label": "待采购/入库", "value": pending_purchase, "trend": "采购流程待处理"},
            {"label": "待出库/配送", "value": pending_outbound, "trend": "仓库与配送待处理"},
            {"label": "待审批", "value": pending_approval, "trend": "订单或采购需审核"},
            {"label": "未收款", "value": unreceived_total, "trend": f"逾期 ¥{overdue_receivable}", "currency": True},
        ],
        "sales": sales,
        "labels": labels,
        "todos": todo_candidates[:8],
        "composition": composition,
        "total_orders": total_orders,
        "finance": {
            "receivable_total": receivable_total,
            "received_total": received_total,
            "unreceived_total": unreceived_total,
            "overdue_receivable": overdue_receivable,
            "month_orders": month_orders,
            "month_receipts": month_receipts,
        },
        "contract_alerts": [
            {
                "id": row.id,
                "contract_no": row.contract_no,
                "name": row.name,
                "end_date": row.end_date.isoformat(),
                "time": due_label(row.end_date),
                "amount": money(row.amount),
            }
            for row in expiring_contracts[:6]
        ],
        "vehicle_alerts": vehicle_alerts[:6],
        "schedules": [
            {
                "id": row.id,
                "task_no": row.task_no,
                "schedule_date": row.schedule_date.isoformat(),
                "planned_start": row.planned_start,
                "planned_end": row.planned_end,
                "task_type": row.task_type,
                "project_name": row.project_name,
                "item_summary": row.item_summary,
                "status": row.status,
            }
            for row in today_schedules
        ],
    }
