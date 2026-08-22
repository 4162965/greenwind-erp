from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import BusinessOrder, BusinessOrderItem, Contract, InvoiceRecord, OutboundOrder, OutboundOrderItem, Product, ProductVariant, Project, ProjectExpense, ProjectSalary, PurchaseOrder, PurchaseOrderItem, PurchaseReceipt, PurchaseReceiptAllocation, ReceiptRecord, User
from ..permissions import accessible_project_ids


router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def parse_date(value: str | None, fallback: date) -> date:
    return date.fromisoformat(value) if value else fallback


def in_range(value: date | None, start: date, end: date) -> bool:
    return bool(value and start <= value <= end)


def days_between(start: date, end: date) -> int:
    return max((end - start).days + 1, 1)


def overlap_days(start_a: date, end_a: date, start_b: date, end_b: date) -> int:
    start = max(start_a, start_b)
    end = min(end_a, end_b)
    if end < start:
        return 0
    return days_between(start, end)


def month_value(value: str) -> int:
    year, month = value.split("-")
    return int(year) * 12 + int(month)


def month_range(start: date, end: date) -> tuple[int, int]:
    return month_value(start.strftime("%Y-%m")), month_value(end.strftime("%Y-%m"))


def money(value: float | int | None) -> float:
    return round(float(value or 0), 2)


def serialize_expense(row: ProjectExpense, db: Session):
    project = db.get(Project, row.project_id)
    return {
        "id": row.id,
        "project_id": row.project_id,
        "project_name": project.name if project else "",
        "expense_date": row.expense_date.isoformat() if row.expense_date else "",
        "expense_type": row.expense_type,
        "amount": money(row.amount),
        "handler": row.handler,
        "source_no": row.source_no,
        "description": row.description,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


def project_allowed_filter(db: Session, user: User, project_id: int | None):
    ids = accessible_project_ids(user, db)
    if ids is None:
        return project_id
    if project_id:
        return project_id if project_id in ids else -1
    return ids


def linked_order_no(prefix: str, source_no: str) -> str:
    return source_no[len(prefix) :] if source_no.startswith(prefix) else ""


def contract_income(contract: Contract, start: date, end: date) -> float:
    billing_start = contract.billing_start_date or contract.effective_date
    contract_start = max(billing_start, contract.effective_date)
    contract_end = contract.end_date
    overlap = overlap_days(contract_start, contract_end, start, end)
    if overlap <= 0:
        return 0
    return float(contract.amount or 0) * overlap / days_between(contract_start, contract_end)


@router.get("/project-expenses")
def list_project_expenses(
    project_id: int | None = Query(default=None),
    start_date: str = Query(default=""),
    end_date: str = Query(default=""),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    today = date.today()
    start = parse_date(start_date or None, date(today.year, 1, 1))
    end = parse_date(end_date or None, date(today.year, 12, 31))
    if end < start:
        start, end = end, start
    allowed = project_allowed_filter(db, user, project_id)
    if allowed == -1 or allowed == []:
        return {"items": [], "total": 0}
    filters = [ProjectExpense.expense_date >= start, ProjectExpense.expense_date <= end]
    if isinstance(allowed, list):
        filters.append(ProjectExpense.project_id.in_(allowed))
    elif allowed:
        filters.append(ProjectExpense.project_id == allowed)
    rows = db.scalars(select(ProjectExpense).where(*filters).order_by(ProjectExpense.expense_date.desc(), ProjectExpense.id.desc())).all()
    return {"items": [serialize_expense(row, db) for row in rows], "total": len(rows)}


@router.post("/project-expenses", status_code=status.HTTP_201_CREATED)
def create_project_expense(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    project_id = int(payload.get("project_id") or 0)
    if not project_id or not db.get(Project, project_id):
        raise HTTPException(status_code=400, detail="请选择项目")
    allowed = project_allowed_filter(db, user, project_id)
    if allowed == -1:
        raise HTTPException(status_code=403, detail="无权为该项目登记费用")
    amount = float(payload.get("amount") or 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="费用金额必须大于0")
    row = ProjectExpense(
        project_id=project_id,
        expense_date=parse_date(payload.get("expense_date"), date.today()),
        expense_type=str(payload.get("expense_type") or "其他费用"),
        amount=amount,
        handler=str(payload.get("handler") or user.display_name or user.username),
        source_no=str(payload.get("source_no") or ""),
        description=str(payload.get("description") or ""),
        status=str(payload.get("status") or "已确认"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_expense(row, db)


@router.put("/project-expenses/{expense_id}")
def update_project_expense(
    expense_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    row = db.get(ProjectExpense, expense_id)
    if not row:
        raise HTTPException(status_code=404, detail="项目费用不存在")
    allowed = project_allowed_filter(db, user, row.project_id)
    if allowed == -1:
        raise HTTPException(status_code=403, detail="无权修改该项目费用")
    if "project_id" in payload and int(payload.get("project_id") or 0) != row.project_id:
        new_project_id = int(payload.get("project_id") or 0)
        if not db.get(Project, new_project_id):
            raise HTTPException(status_code=400, detail="项目不存在")
        allowed = project_allowed_filter(db, user, new_project_id)
        if allowed == -1:
            raise HTTPException(status_code=403, detail="无权改到该项目")
        row.project_id = new_project_id
    for key in ["expense_type", "handler", "source_no", "description", "status"]:
        if key in payload:
            setattr(row, key, str(payload.get(key) or ""))
    if "expense_date" in payload:
        row.expense_date = parse_date(payload.get("expense_date"), row.expense_date)
    if "amount" in payload:
        amount = float(payload.get("amount") or 0)
        if amount <= 0:
            raise HTTPException(status_code=400, detail="费用金额必须大于0")
        row.amount = amount
    db.commit()
    db.refresh(row)
    return serialize_expense(row, db)


@router.delete("/project-expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    row = db.get(ProjectExpense, expense_id)
    if not row:
        raise HTTPException(status_code=404, detail="项目费用不存在")
    allowed = project_allowed_filter(db, user, row.project_id)
    if allowed == -1:
        raise HTTPException(status_code=403, detail="无权删除该项目费用")
    db.delete(row)
    db.commit()


@router.get("/project-costs")
def project_costs(
    project_id: int | None = Query(default=None),
    start_date: str = Query(default=""),
    end_date: str = Query(default=""),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    today = date.today()
    start = parse_date(start_date or None, date(today.year, 1, 1))
    end = parse_date(end_date or None, date(today.year, 12, 31))
    if end < start:
        start, end = end, start

    allowed = project_allowed_filter(db, user, project_id)
    if allowed == -1 or allowed == []:
        return {"items": [], "details": [], "summary": {}, "start_date": start.isoformat(), "end_date": end.isoformat()}

    project_filters = []
    if isinstance(allowed, list):
        project_filters.append(Project.id.in_(allowed))
    elif allowed:
        project_filters.append(Project.id == allowed)
    projects = db.scalars(select(Project).where(*project_filters).order_by(Project.id.desc())).all()
    project_map = {project.id: project for project in projects}
    project_name_map = {project.name: project for project in projects}
    buckets = {
        project.id: {
            "project_id": project.id,
            "project_name": project.name,
            "customer_income": 0.0,
            "purchase_cost": 0.0,
            "stock_out_cost": 0.0,
            "salary_cost": 0.0,
            "other_cost": 0.0,
            "logistics_cost": 0.0,
            "invoice_amount": 0.0,
            "receipt_amount": 0.0,
            "unreceived_amount": 0.0,
            "total_cost": 0.0,
            "profit": 0.0,
            "profit_rate": 0.0,
        }
        for project in projects
    }
    details: list[dict] = []

    for contract in db.scalars(select(Contract).where(Contract.status != "作废")).all():
        if contract.project_id not in buckets:
            continue
        amount = contract_income(contract, start, end)
        if amount <= 0:
            continue
        buckets[contract.project_id]["customer_income"] += amount
        details.append(
            {
                "date": contract.billing_start_date.isoformat() if contract.billing_start_date else contract.effective_date.isoformat(),
                "project_id": contract.project_id,
                "project_name": buckets[contract.project_id]["project_name"],
                "category": "合同收入",
                "source_no": contract.contract_no,
                "description": contract.name,
                "income": money(amount),
                "cost": 0,
            }
        )

    receipt_allocations = db.scalars(select(PurchaseReceiptAllocation).order_by(PurchaseReceiptAllocation.id)).all()
    purchase_nos_with_receipt_cost: set[str] = set()
    for allocation in receipt_allocations:
        receipt = db.get(PurchaseReceipt, allocation.receipt_id)
        allocation_date = (receipt.receipt_date if receipt else None) or allocation.created_at.date()
        if not in_range(allocation_date, start, end):
            continue
        if receipt and receipt.source_purchase_no:
            purchase_nos_with_receipt_cost.add(receipt.source_purchase_no)
        project = project_map.get(allocation.project_id) if allocation.project_id else project_name_map.get(allocation.project_name)
        if not project:
            continue
        cost = float(allocation.quantity or 0) * float(allocation.unit_price or 0)
        if cost <= 0:
            continue
        buckets[project.id]["purchase_cost"] += cost
        product = db.get(Product, allocation.product_id)
        variant = db.get(ProductVariant, allocation.variant_id) if allocation.variant_id else None
        product_name = product.name if product else "收据货品"
        variant_name = (variant.specification or variant.code) if variant else ""
        quantity_text = f"{float(allocation.quantity or 0):g}{allocation.unit or ''}"
        price_text = f"{float(allocation.unit_price or 0):g}"
        details.append(
            {
                "date": allocation_date.isoformat(),
                "project_id": project.id,
                "project_name": project.name,
                "category": "收据分配成本",
                "source_no": receipt.receipt_no if receipt else f"FP-{allocation.id}",
                "description": f"{product_name}{(' ' + variant_name) if variant_name else ''} {quantity_text} × {price_text}",
                "income": 0,
                "cost": money(cost),
            }
        )

    purchase_orders = db.scalars(select(PurchaseOrder).order_by(PurchaseOrder.id)).all()
    for purchase in purchase_orders:
        if purchase.order_no in purchase_nos_with_receipt_cost:
            continue
        purchase_date = purchase.purchase_date or purchase.created_at.date()
        if not in_range(purchase_date, start, end):
            continue
        source_order_no = linked_order_no("CG-", purchase.order_no)
        order = db.scalar(select(BusinessOrder).where(BusinessOrder.order_no == source_order_no)) if source_order_no else None
        project = project_map.get(order.project_id) if order else None
        if not project:
            continue
        items = db.scalars(select(PurchaseOrderItem).where(PurchaseOrderItem.order_id == purchase.id)).all()
        item_cost = sum(float(item.quantity or 0) * float(item.unit_price or 0) for item in items)
        logistics = float(purchase.freight_fee or 0) + float(purchase.hll_fee or 0)
        buckets[project.id]["purchase_cost"] += item_cost
        buckets[project.id]["logistics_cost"] += logistics
        if item_cost:
            details.append(
                {
                    "date": purchase_date.isoformat(),
                    "project_id": project.id,
                    "project_name": project.name,
                    "category": "采购成本",
                    "source_no": purchase.order_no,
                    "description": f"{purchase.supplier or '采购单'}；{len(items)} 条明细",
                    "income": 0,
                    "cost": money(item_cost),
                }
            )
        if logistics:
            details.append(
                {
                    "date": purchase_date.isoformat(),
                    "project_id": project.id,
                    "project_name": project.name,
                    "category": "物流费用",
                    "source_no": purchase.order_no,
                    "description": f"运费 {money(purchase.freight_fee)}，货拉拉 {money(purchase.hll_fee)}",
                    "income": 0,
                    "cost": money(logistics),
                }
            )

    outbound_orders = db.scalars(select(OutboundOrder).order_by(OutboundOrder.id)).all()
    for outbound in outbound_orders:
        outbound_date = outbound.outbound_date or outbound.created_at.date()
        if not in_range(outbound_date, start, end):
            continue
        project = project_name_map.get(outbound.project_name)
        if not project:
            continue
        source_order_no = linked_order_no("CK-", outbound.order_no)
        has_purchase = bool(source_order_no and db.scalar(select(PurchaseOrder.id).where(PurchaseOrder.order_no == f"CG-{source_order_no}")))
        if has_purchase:
            continue
        items = db.scalars(select(OutboundOrderItem).where(OutboundOrderItem.order_id == outbound.id)).all()
        item_cost = sum(float(item.quantity or 0) * float(item.unit_price or 0) for item in items)
        if not item_cost:
            continue
        buckets[project.id]["stock_out_cost"] += item_cost
        details.append(
            {
                "date": outbound_date.isoformat(),
                "project_id": project.id,
                "project_name": project.name,
                "category": "库存领用成本",
                "source_no": outbound.order_no,
                "description": f"{outbound.outbound_type}；{len(items)} 条明细",
                "income": 0,
                "cost": money(item_cost),
            }
        )

    start_month, end_month = month_range(start, end)
    salaries = db.scalars(select(ProjectSalary).order_by(ProjectSalary.salary_month.desc())).all()
    for salary in salaries:
        if salary.project_id not in buckets:
            continue
        current_month = month_value(salary.salary_month)
        if current_month < start_month or current_month > end_month:
            continue
        buckets[salary.project_id]["salary_cost"] += float(salary.amount or 0)
        details.append(
            {
                "date": f"{salary.salary_month}-01",
                "project_id": salary.project_id,
                "project_name": buckets[salary.project_id]["project_name"],
                "category": "养护工资",
                "source_no": salary.salary_month,
                "description": salary.adjustment_reason or "项目养护员工资",
                "income": 0,
                "cost": money(salary.amount),
            }
        )

    expenses = db.scalars(
        select(ProjectExpense).where(ProjectExpense.expense_date >= start, ProjectExpense.expense_date <= end, ProjectExpense.status != "作废").order_by(ProjectExpense.expense_date.desc())
    ).all()
    for expense in expenses:
        if expense.project_id not in buckets:
            continue
        buckets[expense.project_id]["other_cost"] += float(expense.amount or 0)
        details.append(
            {
                "date": expense.expense_date.isoformat(),
                "project_id": expense.project_id,
                "project_name": buckets[expense.project_id]["project_name"],
                "category": expense.expense_type,
                "source_no": expense.source_no or f"FY-{expense.id}",
                "description": expense.description or expense.handler or "项目费用",
                "income": 0,
                "cost": money(expense.amount),
            }
        )

    invoices = db.scalars(select(InvoiceRecord).where(InvoiceRecord.invoice_date >= start, InvoiceRecord.invoice_date <= end, InvoiceRecord.status != "作废")).all()
    for invoice in invoices:
        if invoice.project_id not in buckets:
            continue
        buckets[invoice.project_id]["invoice_amount"] += float(invoice.amount or 0)

    receipts = db.scalars(select(ReceiptRecord).where(ReceiptRecord.receipt_date >= start, ReceiptRecord.receipt_date <= end, ReceiptRecord.status != "作废")).all()
    for receipt in receipts:
        if receipt.project_id not in buckets:
            continue
        buckets[receipt.project_id]["receipt_amount"] += float(receipt.amount or 0)

    items = []
    for bucket in buckets.values():
        bucket["customer_income"] = money(bucket["customer_income"])
        bucket["purchase_cost"] = money(bucket["purchase_cost"])
        bucket["stock_out_cost"] = money(bucket["stock_out_cost"])
        bucket["salary_cost"] = money(bucket["salary_cost"])
        bucket["other_cost"] = money(bucket["other_cost"])
        bucket["logistics_cost"] = money(bucket["logistics_cost"])
        bucket["invoice_amount"] = money(bucket["invoice_amount"])
        bucket["receipt_amount"] = money(bucket["receipt_amount"])
        bucket["unreceived_amount"] = money(bucket["invoice_amount"] - bucket["receipt_amount"])
        bucket["total_cost"] = money(bucket["purchase_cost"] + bucket["stock_out_cost"] + bucket["salary_cost"] + bucket["other_cost"] + bucket["logistics_cost"])
        bucket["profit"] = money(bucket["customer_income"] - bucket["total_cost"])
        bucket["profit_rate"] = round(bucket["profit"] / bucket["customer_income"] * 100, 2) if bucket["customer_income"] else 0
        items.append(bucket)

    items.sort(key=lambda row: row["profit"])
    details.sort(key=lambda row: (row["date"], row["project_name"], row["category"]), reverse=True)
    summary = {
        "customer_income": money(sum(row["customer_income"] for row in items)),
        "purchase_cost": money(sum(row["purchase_cost"] for row in items)),
        "stock_out_cost": money(sum(row["stock_out_cost"] for row in items)),
        "salary_cost": money(sum(row["salary_cost"] for row in items)),
        "other_cost": money(sum(row["other_cost"] for row in items)),
        "logistics_cost": money(sum(row["logistics_cost"] for row in items)),
        "invoice_amount": money(sum(row["invoice_amount"] for row in items)),
        "receipt_amount": money(sum(row["receipt_amount"] for row in items)),
        "unreceived_amount": money(sum(row["unreceived_amount"] for row in items)),
        "total_cost": money(sum(row["total_cost"] for row in items)),
        "profit": money(sum(row["profit"] for row in items)),
    }
    summary["profit_rate"] = round(summary["profit"] / summary["customer_income"] * 100, 2) if summary["customer_income"] else 0
    return {
        "items": items,
        "details": details[:300],
        "summary": summary,
        "total": len(items),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "note": "采购成本按订单生成的采购单归集；已有采购单的订单不再重复统计出库成本。",
    }


@router.get("/order-stats")
def order_stats(
    start_date: str = Query(default=""),
    end_date: str = Query(default=""),
    keyword: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    today = date.today()
    start = parse_date(start_date or None, date(today.year, today.month, 1))
    end = parse_date(end_date or None, today)
    if end < start:
        start, end = end, start

    allowed = project_allowed_filter(db, user, None)
    if allowed == -1 or allowed == []:
        return {"items": [], "summary": {}, "trend": [], "type_stats": [], "total": 0}

    filters = [BusinessOrder.order_date >= start, BusinessOrder.order_date <= end]
    if isinstance(allowed, list):
        filters.append(BusinessOrder.project_id.in_(allowed))
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(
            (BusinessOrder.order_no.like(pattern))
            | (BusinessOrder.project_name.like(pattern))
            | (BusinessOrder.customer_name.like(pattern))
            | (BusinessOrder.requester.like(pattern))
        )
    orders = db.scalars(select(BusinessOrder).where(*filters).order_by(BusinessOrder.order_date.desc(), BusinessOrder.id.desc())).all()
    order_ids = [row.id for row in orders]
    item_rows = db.scalars(select(BusinessOrderItem).where(BusinessOrderItem.order_id.in_(order_ids))).all() if order_ids else []
    items_by_order: dict[int, list[BusinessOrderItem]] = {}
    for item in item_rows:
        items_by_order.setdefault(item.order_id, []).append(item)

    rows = []
    type_map: dict[str, dict] = {}
    status_map: dict[str, int] = {}
    total_amount = 0.0
    for order in orders:
        lines = items_by_order.get(order.id, [])
        amount = sum(float(item.amount or 0) for item in lines)
        total_amount += amount
        type_bucket = type_map.setdefault(order.order_type, {"order_type": order.order_type, "count": 0, "amount": 0.0, "quantity": 0.0})
        type_bucket["count"] += 1
        type_bucket["amount"] += amount
        type_bucket["quantity"] += sum(float(item.quantity or 0) for item in lines)
        status_map[order.status] = status_map.get(order.status, 0) + 1
        rows.append(
            {
                "id": order.id,
                "order_no": order.order_no,
                "order_type": order.order_type,
                "project_name": order.project_name,
                "customer_name": order.customer_name,
                "requester": order.requester,
                "order_date": order.order_date.isoformat() if order.order_date else "",
                "expected_date": order.expected_date.isoformat() if order.expected_date else "",
                "status": order.status,
                "item_count": len(lines),
                "quantity": money(sum(float(item.quantity or 0) for item in lines)),
                "amount": money(amount),
            }
        )

    trend = []
    current = start
    while current <= end:
        day_orders = [row for row in orders if row.order_date == current]
        trend.append({"date": current.isoformat(), "count": len(day_orders)})
        current = date.fromordinal(current.toordinal() + 1)

    return {
        "items": rows,
        "summary": {
            "order_count": len(orders),
            "item_count": len(item_rows),
            "amount": money(total_amount),
            "pending_count": len([row for row in orders if row.status not in {"已完成", "已取消", "已驳回"}]),
        },
        "trend": trend,
        "type_stats": [{**value, "amount": money(value["amount"]), "quantity": money(value["quantity"])} for value in type_map.values()],
        "status_stats": [{"status": key, "count": value} for key, value in status_map.items()],
        "total": len(rows),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }


@router.get("/goods-summary")
def goods_summary(
    keyword: str = Query(default="", max_length=100),
    category: str = Query(default="", max_length=64),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    filters = []
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append((Product.code.like(pattern)) | (Product.name.like(pattern)) | (Product.specification.like(pattern)))
    if category.strip():
        filters.append(Product.category == category.strip())
    products = db.scalars(select(Product).where(*filters).order_by(Product.category, Product.name)).all()
    rows = []
    total_stock_value = 0.0
    total_sale_value = 0.0
    variant_count = 0
    for product in products:
        variants = db.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id).order_by(ProductVariant.sort_order, ProductVariant.id)).all()
        if not variants:
            purchase_value = float(product.stock or 0) * float(product.reference_purchase_price or 0)
            sale_value = float(product.stock or 0) * float(product.sale_price or 0)
            total_stock_value += purchase_value
            total_sale_value += sale_value
            rows.append(
                {
                    "id": product.id,
                    "code": product.code,
                    "name": product.name,
                    "category": product.category,
                    "specification": product.specification,
                    "unit": product.unit,
                    "stock": money(product.stock),
                    "purchase_price": money(product.reference_purchase_price),
                    "sale_price": money(product.sale_price),
                    "monthly_rental_price": money(product.monthly_rental_price),
                    "stock_value": money(purchase_value),
                    "sale_value": money(sale_value),
                    "variant_count": 0,
                    "package_conversion_enabled": product.package_conversion_enabled,
                }
            )
            continue
        variant_count += len(variants)
        stock = sum(float(variant.stock or 0) for variant in variants)
        purchase_value = sum(float(variant.stock or 0) * float(variant.reference_purchase_price or 0) for variant in variants)
        sale_value = sum(float(variant.stock or 0) * float(variant.sale_price or 0) for variant in variants)
        total_stock_value += purchase_value
        total_sale_value += sale_value
        rows.append(
            {
                "id": product.id,
                "code": product.code,
                "name": product.name,
                "category": product.category,
                "specification": "、".join(variant.specification for variant in variants if variant.specification) or product.specification,
                "unit": variants[0].unit if variants else product.unit,
                "stock": money(stock),
                "purchase_price": money(purchase_value / stock) if stock else 0,
                "sale_price": money(sale_value / stock) if stock else 0,
                "monthly_rental_price": money(sum(float(variant.monthly_rental_price or 0) for variant in variants) / len(variants)) if variants else 0,
                "stock_value": money(purchase_value),
                "sale_value": money(sale_value),
                "variant_count": len(variants),
                "package_conversion_enabled": product.package_conversion_enabled,
            }
        )
    categories = db.scalars(select(Product.category).distinct().order_by(Product.category)).all()
    return {
        "items": rows,
        "categories": [item for item in categories if item],
        "summary": {
            "product_count": len(products),
            "variant_count": variant_count,
            "stock_value": money(total_stock_value),
            "sale_value": money(total_sale_value),
        },
        "total": len(rows),
    }
