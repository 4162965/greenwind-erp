from calendar import monthrange
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Contract, InvoiceRecord, Project, ReceivableRecord, ReceiptRecord, User
from ..permissions import accessible_project_ids


router = APIRouter(prefix="/api/v1/finance", tags=["finance"])


def parse_date(value, fallback: date) -> date:
    if not value:
        return fallback
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def money(value) -> float:
    return round(float(value or 0), 2)


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def cycle_months(cycle: str) -> int:
    if "季" in cycle:
        return 3
    if "半年" in cycle:
        return 6
    if "年" in cycle:
        return 12
    if "一次" in cycle:
        return 0
    return 1


def billing_period_label(start: date, end: date, cycle: str) -> str:
    if start.year == end.year and start.month == end.month:
        return start.strftime("%Y-%m")
    return f"{start.strftime('%Y-%m')}至{end.strftime('%Y-%m')}"


def allowed_project_ids(user: User, db: Session):
    return accessible_project_ids(user, db)


def ensure_project_access(project_id: int, user: User, db: Session):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=400, detail="项目不存在")
    ids = allowed_project_ids(user, db)
    if ids is not None and project_id not in ids:
        raise HTTPException(status_code=403, detail="无权操作该项目")
    return project


def contract_name(contract_id: int | None, db: Session) -> str:
    contract = db.get(Contract, contract_id) if contract_id else None
    return contract.name if contract else ""


def serialize_invoice(row: InvoiceRecord, db: Session):
    project = db.get(Project, row.project_id)
    return {
        "id": row.id,
        "invoice_no": row.invoice_no,
        "project_id": row.project_id,
        "project_name": project.name if project else "",
        "contract_id": row.contract_id,
        "contract_name": contract_name(row.contract_id, db),
        "invoice_date": row.invoice_date.isoformat() if row.invoice_date else "",
        "billing_period": row.billing_period,
        "amount": money(row.amount),
        "tax_amount": money(row.tax_amount),
        "invoice_type": row.invoice_type,
        "payer_name": row.payer_name,
        "handler": row.handler,
        "source_no": row.source_no,
        "status": row.status,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


def serialize_receipt(row: ReceiptRecord, db: Session):
    project = db.get(Project, row.project_id)
    invoice = db.get(InvoiceRecord, row.invoice_id) if row.invoice_id else None
    return {
        "id": row.id,
        "receipt_no": row.receipt_no,
        "project_id": row.project_id,
        "project_name": project.name if project else "",
        "contract_id": row.contract_id,
        "contract_name": contract_name(row.contract_id, db),
        "invoice_id": row.invoice_id,
        "invoice_no": invoice.invoice_no if invoice else "",
        "receipt_date": row.receipt_date.isoformat() if row.receipt_date else "",
        "billing_period": row.billing_period,
        "amount": money(row.amount),
        "payment_method": row.payment_method,
        "payer_name": row.payer_name,
        "handler": row.handler,
        "source_no": row.source_no,
        "status": row.status,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


def serialize_receivable(row: ReceivableRecord, db: Session):
    project = db.get(Project, row.project_id)
    contract = db.get(Contract, row.contract_id) if row.contract_id else None
    return {
        "id": row.id,
        "receivable_no": row.receivable_no,
        "project_id": row.project_id,
        "project_name": project.name if project else "",
        "contract_id": row.contract_id,
        "contract_no": contract.contract_no if contract else "",
        "contract_name": contract.name if contract else "",
        "billing_period": row.billing_period,
        "due_date": row.due_date.isoformat() if row.due_date else "",
        "amount": money(row.amount),
        "received_amount": money(row.received_amount),
        "invoice_amount": money(row.invoice_amount),
        "unreceived_amount": money(float(row.amount or 0) - float(row.received_amount or 0)),
        "uninvoiced_amount": money(float(row.amount or 0) - float(row.invoice_amount or 0)),
        "receivable_type": row.receivable_type,
        "status": row.status,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


def project_filter(model, user: User, db: Session, project_id: int | None):
    ids = allowed_project_ids(user, db)
    filters = []
    if ids is not None:
        if not ids:
            return None
        filters.append(model.project_id.in_(ids))
    if project_id:
        ensure_project_access(project_id, user, db)
        filters.append(model.project_id == project_id)
    return filters


def refresh_receivable_status(row: ReceivableRecord, db: Session):
    invoice_amount = db.scalar(
        select(func.coalesce(func.sum(InvoiceRecord.amount), 0)).where(
            InvoiceRecord.project_id == row.project_id,
            InvoiceRecord.contract_id == row.contract_id,
            InvoiceRecord.billing_period == row.billing_period,
            InvoiceRecord.status != "作废",
        )
    ) or 0
    receipt_amount = db.scalar(
        select(func.coalesce(func.sum(ReceiptRecord.amount), 0)).where(
            ReceiptRecord.project_id == row.project_id,
            ReceiptRecord.contract_id == row.contract_id,
            ReceiptRecord.billing_period == row.billing_period,
            ReceiptRecord.status != "作废",
        )
    ) or 0
    row.invoice_amount = float(invoice_amount or 0)
    row.received_amount = float(receipt_amount or 0)
    if row.received_amount >= float(row.amount or 0):
        row.status = "已收款"
    elif row.received_amount > 0:
        row.status = "部分收款"
    elif row.due_date < date.today():
        row.status = "逾期"
    else:
        row.status = "待收款"


@router.get("/receivables")
def list_receivables(
    project_id: int | None = None,
    keyword: str = Query(default="", max_length=100),
    status_text: str = Query(default="", alias="status", max_length=16),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    filters = project_filter(ReceivableRecord, user, db, project_id)
    if filters is None:
        return {"items": [], "total": 0}
    if status_text.strip():
        filters.append(ReceivableRecord.status == status_text.strip())
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(ReceivableRecord.receivable_no.like(pattern), ReceivableRecord.billing_period.like(pattern), ReceivableRecord.notes.like(pattern)))
    rows = db.scalars(select(ReceivableRecord).where(*filters).order_by(ReceivableRecord.due_date.desc(), ReceivableRecord.id.desc())).all()
    for row in rows:
        refresh_receivable_status(row, db)
    db.commit()
    return {"items": [serialize_receivable(row, db) for row in rows], "total": len(rows)}


@router.post("/receivables", status_code=status.HTTP_201_CREATED)
def create_receivable(payload: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    receivable_no = str(payload.get("receivable_no") or "").strip()
    if not receivable_no:
        raise HTTPException(status_code=400, detail="请填写应收编号")
    if db.scalar(select(ReceivableRecord).where(ReceivableRecord.receivable_no == receivable_no)):
        raise HTTPException(status_code=409, detail="应收编号已存在")
    project = ensure_project_access(int(payload.get("project_id") or 0), user, db)
    amount = float(payload.get("amount") or 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="应收金额必须大于0")
    row = ReceivableRecord(
        receivable_no=receivable_no,
        project_id=project.id,
        contract_id=int(payload["contract_id"]) if payload.get("contract_id") else None,
        billing_period=str(payload.get("billing_period") or ""),
        due_date=parse_date(payload.get("due_date"), date.today()),
        amount=amount,
        receivable_type=str(payload.get("receivable_type") or "合同应收"),
        status=str(payload.get("status") or "待收款"),
        notes=str(payload.get("notes") or ""),
    )
    refresh_receivable_status(row, db)
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_receivable(row, db)


@router.put("/receivables/{record_id}")
def update_receivable(record_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row = db.get(ReceivableRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="应收记录不存在")
    ensure_project_access(row.project_id, user, db)
    if "receivable_no" in payload and payload.get("receivable_no") != row.receivable_no:
        if db.scalar(select(ReceivableRecord).where(ReceivableRecord.receivable_no == payload["receivable_no"], ReceivableRecord.id != record_id)):
            raise HTTPException(status_code=409, detail="应收编号已存在")
        row.receivable_no = str(payload.get("receivable_no") or "")
    if "project_id" in payload:
        row.project_id = ensure_project_access(int(payload.get("project_id") or 0), user, db).id
    if "contract_id" in payload:
        row.contract_id = int(payload["contract_id"]) if payload.get("contract_id") else None
    for key in ["billing_period", "receivable_type", "status", "notes"]:
        if key in payload:
            setattr(row, key, str(payload.get(key) or ""))
    if "due_date" in payload:
        row.due_date = parse_date(payload.get("due_date"), row.due_date)
    if "amount" in payload:
        amount = float(payload.get("amount") or 0)
        if amount <= 0:
            raise HTTPException(status_code=400, detail="应收金额必须大于0")
        row.amount = amount
    refresh_receivable_status(row, db)
    db.commit()
    db.refresh(row)
    return serialize_receivable(row, db)


@router.delete("/receivables/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receivable(record_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row = db.get(ReceivableRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="应收记录不存在")
    ensure_project_access(row.project_id, user, db)
    db.delete(row)
    db.commit()


@router.post("/receivables/generate-from-contract/{contract_id}")
def generate_receivables_from_contract(contract_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    ensure_project_access(contract.project_id, user, db)
    start = contract.billing_start_date or contract.effective_date
    end = contract.end_date
    if end < start:
        raise HTTPException(status_code=400, detail="合同结束日期不能早于计费开始日期")
    step = cycle_months(contract.billing_cycle)
    periods = []
    if step == 0:
        periods = [(start, end)]
    else:
        current = start
        while current <= end:
            next_start = add_months(current, step)
            period_end = min(add_months(next_start, 0) if False else next_start, end)
            period_end = min(period_end.replace(day=1) if False else next_start, end)
            period_end = min(add_months(current, step) if step else end, end)
            if period_end > current:
                period_end = period_end.fromordinal(period_end.toordinal() - 1) if period_end < end else end
            periods.append((current, period_end))
            current = add_months(current, step)
    if not periods:
        raise HTTPException(status_code=400, detail="没有可生成的账期")
    total_days = max((end - start).days + 1, 1)
    created = 0
    skipped = 0
    for index, (period_start, period_end) in enumerate(periods, start=1):
        label = billing_period_label(period_start, period_end, contract.billing_cycle)
        receivable_no = f"YS-{contract.contract_no}-{index:02d}"[:64]
        exists = db.scalar(select(ReceivableRecord).where(ReceivableRecord.receivable_no == receivable_no))
        if exists:
            skipped += 1
            continue
        amount = float(contract.amount or 0) * ((period_end - period_start).days + 1) / total_days
        row = ReceivableRecord(
            receivable_no=receivable_no,
            project_id=contract.project_id,
            contract_id=contract.id,
            billing_period=label,
            due_date=period_start,
            amount=round(amount, 2),
            receivable_type="合同应收",
            notes=f"由合同 {contract.contract_no} 自动生成",
        )
        refresh_receivable_status(row, db)
        db.add(row)
        created += 1
    db.commit()
    return {"status": "ok", "created": created, "skipped": skipped}


@router.get("/invoices")
def list_invoices(
    project_id: int | None = None,
    keyword: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    filters = project_filter(InvoiceRecord, user, db, project_id)
    if filters is None:
        return {"items": [], "total": 0}
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(InvoiceRecord.invoice_no.like(pattern), InvoiceRecord.payer_name.like(pattern), InvoiceRecord.source_no.like(pattern), InvoiceRecord.billing_period.like(pattern)))
    rows = db.scalars(select(InvoiceRecord).where(*filters).order_by(InvoiceRecord.invoice_date.desc(), InvoiceRecord.id.desc())).all()
    return {"items": [serialize_invoice(row, db) for row in rows], "total": len(rows)}


@router.post("/invoices", status_code=status.HTTP_201_CREATED)
def create_invoice(payload: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    invoice_no = str(payload.get("invoice_no") or "").strip()
    if not invoice_no:
        raise HTTPException(status_code=400, detail="请填写发票号")
    if db.scalar(select(InvoiceRecord).where(InvoiceRecord.invoice_no == invoice_no)):
        raise HTTPException(status_code=409, detail="发票号已存在")
    project = ensure_project_access(int(payload.get("project_id") or 0), user, db)
    amount = float(payload.get("amount") or 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="开票金额必须大于0")
    row = InvoiceRecord(
        invoice_no=invoice_no,
        project_id=project.id,
        contract_id=int(payload["contract_id"]) if payload.get("contract_id") else None,
        invoice_date=parse_date(payload.get("invoice_date"), date.today()),
        billing_period=str(payload.get("billing_period") or ""),
        amount=amount,
        tax_amount=float(payload.get("tax_amount") or 0),
        invoice_type=str(payload.get("invoice_type") or "普通发票"),
        payer_name=str(payload.get("payer_name") or ""),
        handler=str(payload.get("handler") or user.display_name or user.username),
        source_no=str(payload.get("source_no") or ""),
        status=str(payload.get("status") or "已开票"),
        notes=str(payload.get("notes") or ""),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_invoice(row, db)


@router.put("/invoices/{record_id}")
def update_invoice(record_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row = db.get(InvoiceRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="发票记录不存在")
    ensure_project_access(row.project_id, user, db)
    if "invoice_no" in payload and payload.get("invoice_no") != row.invoice_no:
        if db.scalar(select(InvoiceRecord).where(InvoiceRecord.invoice_no == payload["invoice_no"], InvoiceRecord.id != record_id)):
            raise HTTPException(status_code=409, detail="发票号已存在")
        row.invoice_no = str(payload.get("invoice_no") or "")
    if "project_id" in payload:
        row.project_id = ensure_project_access(int(payload.get("project_id") or 0), user, db).id
    for key in ["billing_period", "invoice_type", "payer_name", "handler", "source_no", "status", "notes"]:
        if key in payload:
            setattr(row, key, str(payload.get(key) or ""))
    if "contract_id" in payload:
        row.contract_id = int(payload["contract_id"]) if payload.get("contract_id") else None
    if "invoice_date" in payload:
        row.invoice_date = parse_date(payload.get("invoice_date"), row.invoice_date)
    if "amount" in payload:
        amount = float(payload.get("amount") or 0)
        if amount <= 0:
            raise HTTPException(status_code=400, detail="开票金额必须大于0")
        row.amount = amount
    if "tax_amount" in payload:
        row.tax_amount = float(payload.get("tax_amount") or 0)
    db.commit()
    db.refresh(row)
    return serialize_invoice(row, db)


@router.delete("/invoices/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(record_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row = db.get(InvoiceRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="发票记录不存在")
    ensure_project_access(row.project_id, user, db)
    db.delete(row)
    db.commit()


@router.get("/receipts")
def list_receipts(
    project_id: int | None = None,
    keyword: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    filters = project_filter(ReceiptRecord, user, db, project_id)
    if filters is None:
        return {"items": [], "total": 0}
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(ReceiptRecord.receipt_no.like(pattern), ReceiptRecord.payer_name.like(pattern), ReceiptRecord.source_no.like(pattern), ReceiptRecord.billing_period.like(pattern)))
    rows = db.scalars(select(ReceiptRecord).where(*filters).order_by(ReceiptRecord.receipt_date.desc(), ReceiptRecord.id.desc())).all()
    return {"items": [serialize_receipt(row, db) for row in rows], "total": len(rows)}


@router.post("/receipts", status_code=status.HTTP_201_CREATED)
def create_receipt(payload: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    receipt_no = str(payload.get("receipt_no") or "").strip()
    if not receipt_no:
        raise HTTPException(status_code=400, detail="请填写收款单号")
    if db.scalar(select(ReceiptRecord).where(ReceiptRecord.receipt_no == receipt_no)):
        raise HTTPException(status_code=409, detail="收款单号已存在")
    project = ensure_project_access(int(payload.get("project_id") or 0), user, db)
    amount = float(payload.get("amount") or 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="收款金额必须大于0")
    row = ReceiptRecord(
        receipt_no=receipt_no,
        project_id=project.id,
        contract_id=int(payload["contract_id"]) if payload.get("contract_id") else None,
        invoice_id=int(payload["invoice_id"]) if payload.get("invoice_id") else None,
        receipt_date=parse_date(payload.get("receipt_date"), date.today()),
        billing_period=str(payload.get("billing_period") or ""),
        amount=amount,
        payment_method=str(payload.get("payment_method") or "银行转账"),
        payer_name=str(payload.get("payer_name") or ""),
        handler=str(payload.get("handler") or user.display_name or user.username),
        source_no=str(payload.get("source_no") or ""),
        status=str(payload.get("status") or "已收款"),
        notes=str(payload.get("notes") or ""),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_receipt(row, db)


@router.put("/receipts/{record_id}")
def update_receipt(record_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row = db.get(ReceiptRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="收款记录不存在")
    ensure_project_access(row.project_id, user, db)
    if "receipt_no" in payload and payload.get("receipt_no") != row.receipt_no:
        if db.scalar(select(ReceiptRecord).where(ReceiptRecord.receipt_no == payload["receipt_no"], ReceiptRecord.id != record_id)):
            raise HTTPException(status_code=409, detail="收款单号已存在")
        row.receipt_no = str(payload.get("receipt_no") or "")
    if "project_id" in payload:
        row.project_id = ensure_project_access(int(payload.get("project_id") or 0), user, db).id
    for key in ["billing_period", "payment_method", "payer_name", "handler", "source_no", "status", "notes"]:
        if key in payload:
            setattr(row, key, str(payload.get(key) or ""))
    if "contract_id" in payload:
        row.contract_id = int(payload["contract_id"]) if payload.get("contract_id") else None
    if "invoice_id" in payload:
        row.invoice_id = int(payload["invoice_id"]) if payload.get("invoice_id") else None
    if "receipt_date" in payload:
        row.receipt_date = parse_date(payload.get("receipt_date"), row.receipt_date)
    if "amount" in payload:
        amount = float(payload.get("amount") or 0)
        if amount <= 0:
            raise HTTPException(status_code=400, detail="收款金额必须大于0")
        row.amount = amount
    db.commit()
    db.refresh(row)
    return serialize_receipt(row, db)


@router.delete("/receipts/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receipt(record_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row = db.get(ReceiptRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="收款记录不存在")
    ensure_project_access(row.project_id, user, db)
    db.delete(row)
    db.commit()


@router.get("/summary")
def finance_summary(project_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    invoice_filters = project_filter(InvoiceRecord, user, db, project_id)
    receipt_filters = project_filter(ReceiptRecord, user, db, project_id)
    if invoice_filters is None or receipt_filters is None:
        return {"invoice_amount": 0, "receipt_amount": 0, "unreceived_amount": 0}
    invoice_amount = db.scalar(select(func.coalesce(func.sum(InvoiceRecord.amount), 0)).where(*invoice_filters, InvoiceRecord.status != "作废")) or 0
    receipt_amount = db.scalar(select(func.coalesce(func.sum(ReceiptRecord.amount), 0)).where(*receipt_filters, ReceiptRecord.status != "作废")) or 0
    return {"invoice_amount": money(invoice_amount), "receipt_amount": money(receipt_amount), "unreceived_amount": money(float(invoice_amount) - float(receipt_amount))}
