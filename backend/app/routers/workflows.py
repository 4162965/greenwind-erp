from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import ApprovalRequest, ApprovalRule, BusinessOrder, Project, User


router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


def serialize_rule(rule: ApprovalRule, db: Session):
    project = db.get(Project, rule.project_id)
    return {
        "id": rule.id,
        "project_id": rule.project_id,
        "project_name": project.name if project else "",
        "purchase_requires_approval": rule.purchase_requires_approval,
        "exchange_annual_limit": float(rule.exchange_annual_limit or 0),
        "approver_role": rule.approver_role,
        "approver_name": rule.approver_name,
        "status": rule.status,
        "notes": rule.notes,
        "created_at": rule.created_at.isoformat() if rule.created_at else "",
    }


def serialize_request(row: ApprovalRequest):
    return {
        "id": row.id,
        "request_no": row.request_no,
        "approval_type": row.approval_type,
        "source_type": row.source_type,
        "source_id": row.source_id,
        "source_no": row.source_no,
        "project_id": row.project_id,
        "project_name": row.project_name,
        "applicant": row.applicant,
        "amount": float(row.amount or 0),
        "reason": row.reason,
        "approver_role": row.approver_role,
        "approver_name": row.approver_name,
        "status": row.status,
        "decision_comment": row.decision_comment,
        "decided_by": row.decided_by,
        "decided_at": row.decided_at.isoformat() if row.decided_at else "",
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


def request_no(source_no: str) -> str:
    return f"SP-{source_no or int(datetime.now(UTC).timestamp())}"[:64]


@router.get("/rules")
def list_rules(
    keyword: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    filters = []
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        project_ids = db.scalars(select(Project.id).where(Project.name.like(pattern))).all()
        filters.append(or_(ApprovalRule.approver_name.like(pattern), ApprovalRule.project_id.in_(project_ids or [-1])))
    rows = db.scalars(select(ApprovalRule).where(*filters).order_by(ApprovalRule.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(ApprovalRule).where(*filters)) or 0
    return {"items": [serialize_rule(row, db) for row in rows], "total": total}


@router.post("/rules", status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: dict,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    project_id = int(payload.get("project_id") or 0)
    if not db.get(Project, project_id):
        raise HTTPException(status_code=400, detail="项目不存在")
    if db.scalar(select(ApprovalRule).where(ApprovalRule.project_id == project_id)):
        raise HTTPException(status_code=409, detail="该项目已设置审批规则")
    rule = ApprovalRule(
        project_id=project_id,
        purchase_requires_approval=bool(payload.get("purchase_requires_approval") or False),
        exchange_annual_limit=float(payload.get("exchange_annual_limit") or 0),
        approver_role=str(payload.get("approver_role") or "经理"),
        approver_name=str(payload.get("approver_name") or ""),
        status=str(payload.get("status") or "启用"),
        notes=str(payload.get("notes") or ""),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return serialize_rule(rule, db)


@router.put("/rules/{rule_id}")
def update_rule(
    rule_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    rule = db.get(ApprovalRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="审批规则不存在")
    if "project_id" in payload and payload.get("project_id") != rule.project_id:
        project_id = int(payload.get("project_id") or 0)
        if not db.get(Project, project_id):
            raise HTTPException(status_code=400, detail="项目不存在")
        if db.scalar(select(ApprovalRule).where(ApprovalRule.project_id == project_id, ApprovalRule.id != rule_id)):
            raise HTTPException(status_code=409, detail="该项目已设置审批规则")
        rule.project_id = project_id
    for key in ["purchase_requires_approval", "exchange_annual_limit", "approver_role", "approver_name", "status", "notes"]:
        if key not in payload:
            continue
        if key == "purchase_requires_approval":
            setattr(rule, key, bool(payload.get(key)))
        elif key == "exchange_annual_limit":
            setattr(rule, key, float(payload.get(key) or 0))
        else:
            setattr(rule, key, str(payload.get(key) or ""))
    db.commit()
    db.refresh(rule)
    return serialize_rule(rule, db)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    rule = db.get(ApprovalRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="审批规则不存在")
    db.delete(rule)
    db.commit()


@router.get("/requests")
def list_requests(
    keyword: str = Query(default="", max_length=100),
    status_text: str = Query(default="", alias="status", max_length=16),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    filters = []
    if status_text.strip():
        filters.append(ApprovalRequest.status == status_text.strip())
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(ApprovalRequest.request_no.like(pattern), ApprovalRequest.source_no.like(pattern), ApprovalRequest.project_name.like(pattern), ApprovalRequest.reason.like(pattern)))
    rows = db.scalars(select(ApprovalRequest).where(*filters).order_by(ApprovalRequest.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(ApprovalRequest).where(*filters)) or 0
    return {"items": [serialize_request(row) for row in rows], "total": total}


@router.post("/requests")
def create_request(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    source_no = str(payload.get("source_no") or "").strip()
    generated_no = str(payload.get("request_no") or request_no(source_no)).strip()
    if db.scalar(select(ApprovalRequest).where(ApprovalRequest.request_no == generated_no)):
        raise HTTPException(status_code=409, detail="审批单号已存在")
    project = db.get(Project, int(payload["project_id"])) if payload.get("project_id") else None
    row = ApprovalRequest(
        request_no=generated_no,
        approval_type=str(payload.get("approval_type") or "手工审批"),
        source_type=str(payload.get("source_type") or "手工"),
        source_id=int(payload["source_id"]) if payload.get("source_id") else None,
        source_no=source_no,
        project_id=project.id if project else None,
        project_name=str(payload.get("project_name") or (project.name if project else "")),
        applicant=str(payload.get("applicant") or user.display_name or user.username),
        amount=float(payload.get("amount") or 0),
        reason=str(payload.get("reason") or ""),
        approver_role=str(payload.get("approver_role") or "经理"),
        approver_name=str(payload.get("approver_name") or ""),
        status="待审批",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_request(row)


@router.post("/requests/{request_id}/decision")
def decide_request(
    request_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    row = db.get(ApprovalRequest, request_id)
    if not row:
        raise HTTPException(status_code=404, detail="审批记录不存在")
    decision = str(payload.get("status") or "").strip()
    if decision not in {"已通过", "已驳回"}:
        raise HTTPException(status_code=400, detail="审批结果只能是已通过或已驳回")
    row.status = decision
    row.decision_comment = str(payload.get("decision_comment") or "")
    row.decided_by = user.display_name or user.username
    row.decided_at = datetime.now(UTC)
    if row.source_type == "订单" and row.source_id:
        order = db.get(BusinessOrder, row.source_id)
        if order and order.status == "待审批":
            order.status = "待处理" if decision == "已通过" else "已驳回"
    db.commit()
    db.refresh(row)
    return serialize_request(row)
