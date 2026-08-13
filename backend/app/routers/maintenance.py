from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import BusinessOrder, BusinessOrderItem, Employee, MaintenancePlan, MaintenanceRecord, Project, User
from ..permissions import can_access_project, employee_for_user, require_module


router = APIRouter(prefix="/api/v1/maintenance", tags=["maintenance"])


def parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def next_no(prefix: str, db: Session, model, field_name: str) -> str:
    today = date.today().strftime("%Y%m%d")
    count = db.scalar(select(func.count()).select_from(model)) or 0
    return f"{prefix}-{today}-{int(count) + 1:03d}"[:64]


def employee_name(employee_id: int | None, db: Session) -> str:
    if not employee_id:
        return ""
    employee = db.get(Employee, employee_id)
    return employee.name if employee else ""


def plan_payload(plan: MaintenancePlan, db: Session):
    return {
        "id": plan.id,
        "plan_no": plan.plan_no,
        "project_id": plan.project_id,
        "project_name": plan.project_name,
        "maintainer_id": plan.maintainer_id,
        "maintainer_name": employee_name(plan.maintainer_id, db),
        "area_description": plan.area_description,
        "frequency_type": plan.frequency_type,
        "frequency_value": plan.frequency_value,
        "service_content": plan.service_content,
        "start_date": plan.start_date.isoformat() if plan.start_date else None,
        "end_date": plan.end_date.isoformat() if plan.end_date else None,
        "next_due_date": plan.next_due_date.isoformat() if plan.next_due_date else None,
        "reminder_days": plan.reminder_days,
        "status": plan.status,
        "notes": plan.notes,
        "created_at": plan.created_at.isoformat() if plan.created_at else "",
    }


def record_payload(record: MaintenanceRecord, db: Session):
    return {
        "id": record.id,
        "record_no": record.record_no,
        "plan_id": record.plan_id,
        "project_id": record.project_id,
        "project_name": record.project_name,
        "maintainer_id": record.maintainer_id,
        "maintainer_name": employee_name(record.maintainer_id, db),
        "service_date": record.service_date.isoformat() if record.service_date else None,
        "area_description": record.area_description,
        "work_content": record.work_content,
        "site_issue": record.site_issue,
        "handle_result": record.handle_result,
        "photos": record.photos,
        "customer_feedback": record.customer_feedback,
        "next_plan_date": record.next_plan_date.isoformat() if record.next_plan_date else None,
        "generated_order_no": record.generated_order_no,
        "status": record.status,
        "notes": record.notes,
        "created_at": record.created_at.isoformat() if record.created_at else "",
    }


def validate_project(project_id: int, user: User, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if not can_access_project(user, project_id, db):
        raise HTTPException(status_code=403, detail="无权访问该项目")
    return project


def validate_employee(employee_id: int | None, db: Session):
    if employee_id and not db.get(Employee, employee_id):
        raise HTTPException(status_code=400, detail="养护员不存在")


@router.get("/plans")
def list_plans(
    keyword: str = Query(default="", max_length=100),
    project_id: int | None = None,
    include_disabled: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_module(user, "schedule_workflow")
    filters = []
    if not include_disabled:
        filters.append(MaintenancePlan.status == "启用")
    if project_id:
        validate_project(project_id, user, db)
        filters.append(MaintenancePlan.project_id == project_id)
    elif not can_access_project(user, None, db):
        from ..permissions import accessible_project_ids

        ids = accessible_project_ids(user, db)
        if ids is not None:
            if not ids:
                return {"items": [], "total": 0}
            filters.append(MaintenancePlan.project_id.in_(ids))
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(MaintenancePlan.plan_no.like(pattern), MaintenancePlan.project_name.like(pattern), MaintenancePlan.area_description.like(pattern), MaintenancePlan.service_content.like(pattern)))
    items = db.scalars(select(MaintenancePlan).where(*filters).order_by(MaintenancePlan.id.desc())).all()
    return {"items": [plan_payload(item, db) for item in items], "total": len(items)}


@router.post("/plans", status_code=status.HTTP_201_CREATED)
def create_plan(payload: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "schedule_workflow")
    project = validate_project(int(payload.get("project_id") or 0), user, db)
    maintainer_id = int(payload["maintainer_id"]) if payload.get("maintainer_id") else None
    validate_employee(maintainer_id, db)
    plan_no = str(payload.get("plan_no") or "").strip() or next_no("YH-JH", db, MaintenancePlan, "plan_no")
    if db.scalar(select(MaintenancePlan).where(MaintenancePlan.plan_no == plan_no)):
        raise HTTPException(status_code=409, detail="养护计划编号已存在")
    plan = MaintenancePlan(
        plan_no=plan_no,
        project_id=project.id,
        project_name=project.name,
        maintainer_id=maintainer_id,
        area_description=str(payload.get("area_description") or "全部区域"),
        frequency_type=str(payload.get("frequency_type") or "每月次数"),
        frequency_value=str(payload.get("frequency_value") or ""),
        service_content=str(payload.get("service_content") or ""),
        start_date=parse_date(payload.get("start_date")),
        end_date=parse_date(payload.get("end_date")),
        next_due_date=parse_date(payload.get("next_due_date")),
        reminder_days=int(payload.get("reminder_days") or 2),
        status=str(payload.get("status") or "启用"),
        notes=str(payload.get("notes") or ""),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan_payload(plan, db)


@router.put("/plans/{plan_id}")
def update_plan(plan_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "schedule_workflow")
    plan = db.get(MaintenancePlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="养护计划不存在")
    validate_project(plan.project_id, user, db)
    if "project_id" in payload and payload.get("project_id"):
        project = validate_project(int(payload["project_id"]), user, db)
        plan.project_id = project.id
        plan.project_name = project.name
    if "maintainer_id" in payload:
        plan.maintainer_id = int(payload["maintainer_id"]) if payload.get("maintainer_id") else None
        validate_employee(plan.maintainer_id, db)
    for key in ["area_description", "frequency_type", "frequency_value", "service_content", "status", "notes"]:
        if key in payload:
            setattr(plan, key, str(payload.get(key) or ""))
    for key in ["start_date", "end_date", "next_due_date"]:
        if key in payload:
            setattr(plan, key, parse_date(payload.get(key)))
    if "reminder_days" in payload:
        plan.reminder_days = int(payload.get("reminder_days") or 0)
    db.commit()
    db.refresh(plan)
    return plan_payload(plan, db)


@router.get("/records")
def list_records(
    keyword: str = Query(default="", max_length=100),
    project_id: int | None = None,
    service_date: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_module(user, "schedule_workflow")
    filters = []
    if project_id:
        validate_project(project_id, user, db)
        filters.append(MaintenanceRecord.project_id == project_id)
    elif not can_access_project(user, None, db):
        from ..permissions import accessible_project_ids

        ids = accessible_project_ids(user, db)
        if ids is not None:
            if not ids:
                return {"items": [], "total": 0}
            filters.append(MaintenanceRecord.project_id.in_(ids))
    if service_date:
        filters.append(MaintenanceRecord.service_date == service_date)
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(MaintenanceRecord.record_no.like(pattern), MaintenanceRecord.project_name.like(pattern), MaintenanceRecord.work_content.like(pattern), MaintenanceRecord.site_issue.like(pattern)))
    items = db.scalars(select(MaintenanceRecord).where(*filters).order_by(MaintenanceRecord.service_date.desc(), MaintenanceRecord.id.desc())).all()
    return {"items": [record_payload(item, db) for item in items], "total": len(items)}


@router.post("/records", status_code=status.HTTP_201_CREATED)
def create_record(payload: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "schedule_workflow")
    plan_id = int(payload["plan_id"]) if payload.get("plan_id") else None
    plan = db.get(MaintenancePlan, plan_id) if plan_id else None
    project_id = int(payload.get("project_id") or (plan.project_id if plan else 0))
    project = validate_project(project_id, user, db)
    maintainer_id = int(payload["maintainer_id"]) if payload.get("maintainer_id") else (plan.maintainer_id if plan else None)
    validate_employee(maintainer_id, db)
    record_no = str(payload.get("record_no") or "").strip() or next_no("YH-JL", db, MaintenanceRecord, "record_no")
    if db.scalar(select(MaintenanceRecord).where(MaintenanceRecord.record_no == record_no)):
        raise HTTPException(status_code=409, detail="养护记录编号已存在")
    record = MaintenanceRecord(
        record_no=record_no,
        plan_id=plan_id,
        project_id=project.id,
        project_name=project.name,
        maintainer_id=maintainer_id,
        service_date=parse_date(payload.get("service_date")) or date.today(),
        area_description=str(payload.get("area_description") or (plan.area_description if plan else "")),
        work_content=str(payload.get("work_content") or ""),
        site_issue=str(payload.get("site_issue") or ""),
        handle_result=str(payload.get("handle_result") or ""),
        photos=str(payload.get("photos") or ""),
        customer_feedback=str(payload.get("customer_feedback") or ""),
        next_plan_date=parse_date(payload.get("next_plan_date")),
        status=str(payload.get("status") or "已完成"),
        notes=str(payload.get("notes") or ""),
    )
    db.add(record)
    if plan and record.next_plan_date:
        plan.next_due_date = record.next_plan_date
    elif plan and plan.frequency_type == "每月次数":
        plan.next_due_date = record.service_date + timedelta(days=7)
    db.commit()
    db.refresh(record)
    return record_payload(record, db)


@router.post("/records/{record_id}/create-order")
def create_order_from_record(record_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "orders")
    record = db.get(MaintenanceRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="养护记录不存在")
    validate_project(record.project_id, user, db)
    if record.generated_order_no:
        existing = db.scalar(select(BusinessOrder).where(BusinessOrder.order_no == record.generated_order_no))
        if existing:
            return {"status": "exists", "order_id": existing.id, "order_no": existing.order_no}
    action_type = str(payload.get("action_type") or "换花订单")
    order_no = str(payload.get("order_no") or "").strip() or next_no("YH-DD", db, BusinessOrder, "order_no")
    if db.scalar(select(BusinessOrder).where(BusinessOrder.order_no == order_no)):
        raise HTTPException(status_code=409, detail="订单号已存在")
    order = BusinessOrder(
        order_no=order_no,
        order_type=action_type,
        project_id=record.project_id,
        project_name=record.project_name,
        requester=employee_name(record.maintainer_id, db) or user.display_name,
        order_date=date.today(),
        expected_date=parse_date(payload.get("expected_date")),
        priority=str(payload.get("priority") or "普通"),
        need_purchase=bool(payload.get("need_purchase") if payload.get("need_purchase") is not None else True),
        need_delivery=bool(payload.get("need_delivery") if payload.get("need_delivery") is not None else True),
        status="待处理",
        notes=f"由养护记录 {record.record_no} 生成；现场问题：{record.site_issue}；处理建议：{record.handle_result}",
    )
    db.add(order)
    db.flush()
    record.generated_order_no = order.order_no
    db.commit()
    db.refresh(order)
    return {"status": "created", "order_id": order.id, "order_no": order.order_no}
