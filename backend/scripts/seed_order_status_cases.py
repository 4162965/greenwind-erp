from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import delete, select

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, SessionLocal, engine
from app.migrations import upgrade_legacy_sqlite
from app.models import (
    ApprovalRequest,
    BusinessOrder,
    BusinessOrderItem,
    Customer,
    Employee,
    OutboundOrder,
    OutboundOrderItem,
    Product,
    ProductVariant,
    Project,
    PurchaseOrder,
    PurchaseOrderItem,
    ScheduleTask,
    Vehicle,
)


TODAY = date.today()
PREFIX = "ZT"


def one(db, model, fallback=None):
    return db.scalar(select(model).order_by(model.id)) or fallback


def add(db, obj):
    db.add(obj)
    db.flush()
    return obj


def cleanup(db):
    order_nos = [row[0] for row in db.execute(select(BusinessOrder.order_no).where(BusinessOrder.order_no.like(f"{PREFIX}%"))).all()]
    purchase_nos = [f"CG-{no}" for no in order_nos]
    outbound_nos = [f"CK-{no}" for no in order_nos]
    schedule_nos = [f"RC-{no}" for no in order_nos] + [f"RC-CK-{no}" for no in order_nos]
    for model, column, values in [
        (ApprovalRequest, ApprovalRequest.source_no, order_nos),
        (ScheduleTask, ScheduleTask.task_no, schedule_nos),
        (OutboundOrderItem, OutboundOrderItem.order_id, [row[0] for row in db.execute(select(OutboundOrder.id).where(OutboundOrder.order_no.in_(outbound_nos))).all()]),
        (OutboundOrder, OutboundOrder.order_no, outbound_nos),
        (PurchaseOrderItem, PurchaseOrderItem.order_id, [row[0] for row in db.execute(select(PurchaseOrder.id).where(PurchaseOrder.order_no.in_(purchase_nos))).all()]),
        (PurchaseOrder, PurchaseOrder.order_no, purchase_nos),
        (BusinessOrderItem, BusinessOrderItem.order_id, [row[0] for row in db.execute(select(BusinessOrder.id).where(BusinessOrder.order_no.in_(order_nos))).all()]),
        (BusinessOrder, BusinessOrder.order_no, order_nos),
    ]:
        if values:
            db.execute(delete(model).where(column.in_(values)))
    db.flush()


def ensure_fixture(db):
    customer = one(db, Customer)
    if not customer:
        customer = add(db, Customer(name="状态测试客户", customer_type="项目客户", project_name="状态测试项目", contact_person="测试联系人", phone="13800000000", address="状态测试地址", status="启用"))
    employee = one(db, Employee)
    if not employee:
        employee = add(db, Employee(name="状态测试客服", phone="13800000001", department="客服部", position="客服", status="在职"))
    purchaser = db.scalar(select(Employee).where(Employee.position.like("%采购%")).order_by(Employee.id))
    if not purchaser:
        purchaser = add(db, Employee(name="状态测试采购", phone="13800000002", department="采购部", position="采购", status="在职"))
    driver = db.scalar(select(Employee).where(Employee.position.like("%司机%")).order_by(Employee.id))
    if not driver:
        driver = add(db, Employee(name="状态测试司机", phone="13800000003", department="配送部", position="司机", status="在职"))
    assistant = db.scalar(select(Employee).where(Employee.position.like("%跟车%")).order_by(Employee.id))
    if not assistant:
        assistant = add(db, Employee(name="状态测试跟车", phone="13800000004", department="配送部", position="跟车配送", status="在职"))
    vehicle = one(db, Vehicle)
    if not vehicle:
        vehicle = add(db, Vehicle(plate_no="粤A-T001", vehicle_type="小货车", driver_name=driver.name, status="可用"))
    project = one(db, Project)
    if not project:
        project = add(
            db,
            Project(
                code="ZT-PROJECT-001",
                name="状态测试项目",
                customer_id=customer.id,
                business_types="租摆,配送",
                plant_source="新采购",
                supervisor_id=employee.id,
                customer_service_id=employee.id,
                address=customer.address,
                status="进行中",
                start_date=TODAY,
            ),
        )
    product = one(db, Product)
    if not product:
        product = add(db, Product(code="ZT-P001", name="状态测试绿萝", category="植物", unit="盆", purchase_unit="盆", sale_price=18, reference_purchase_price=8, monthly_rental_price=6, stock=100, status="启用"))
    variant = db.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id).order_by(ProductVariant.sort_order, ProductVariant.id))
    if not variant:
        variant = add(db, ProductVariant(product_id=product.id, code=f"{product.code}-1", specification="高30cm", specification_values='{"高度":"30cm"}', unit=product.unit, is_default=True, sort_order=1, reference_purchase_price=8, sale_price=18, monthly_rental_price=6, stock=100, status="启用"))
    employee = one(db, Employee)
    purchaser = db.scalar(select(Employee).where(Employee.position.like("%采购%")).order_by(Employee.id)) or employee
    driver = db.scalar(select(Employee).where(Employee.position.like("%司机%")).order_by(Employee.id)) or employee
    assistant = db.scalar(select(Employee).where(Employee.id != (driver.id if driver else 0)).order_by(Employee.id)) or driver
    vehicle = one(db, Vehicle)
    customer = one(db, Customer)
    project = one(db, Project)
    product = one(db, Product)
    variant = db.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id).order_by(ProductVariant.sort_order, ProductVariant.id)) if product else None
    if not all([employee, purchaser, driver, assistant, customer, project, product]):
        raise RuntimeError("基础资料不足，请先创建员工、客户、项目、商品后再生成订单状态测试数据。")
    return employee, purchaser, driver, assistant, vehicle, customer, project, product, variant


def make_order(db, no, order_type, status, project, customer, requester, product, variant, idx, need_purchase=True, need_delivery=True):
    order = add(
        db,
        BusinessOrder(
            order_no=no,
            order_type=order_type,
            project_id=project.id,
            project_name=project.name,
            customer_name=customer.name,
            requester=requester.name,
            contact_phone=requester.phone,
            order_date=TODAY,
            expected_date=TODAY + timedelta(days=idx),
            priority="普通" if idx % 3 else "加急",
            need_purchase=need_purchase,
            need_delivery=need_delivery,
            status=status,
            notes=f"状态测试：{status}",
        ),
    )
    unit = variant.unit if variant else product.unit
    price = float((variant.sale_price or variant.monthly_rental_price) if variant else (product.sale_price or product.monthly_rental_price) or 18)
    add(
        db,
        BusinessOrderItem(
            order_id=order.id,
            product_id=product.id,
            variant_id=variant.id if variant else None,
            product_name=product.name,
            variant_name=(variant.specification or variant.code) if variant else product.specification,
            location_text=f"状态测试区域{idx}",
            quantity=idx,
            unit=unit,
            unit_price=price,
            amount=idx * price,
            notes="状态测试明细",
        ),
    )
    return order


def add_purchase(db, order, purchaser, product, variant, status):
    item = db.scalar(select(BusinessOrderItem).where(BusinessOrderItem.order_id == order.id))
    purchase = add(
        db,
        PurchaseOrder(
            order_no=f"CG-{order.order_no}",
            supplier="状态测试供应商",
            purchaser=purchaser.name,
            purchase_date=TODAY,
            delivery_method="入库",
            freight_fee=20,
            hll_fee=0,
            status=status,
            notes=f"状态测试采购，来源订单 {order.order_no}",
        ),
    )
    add(
        db,
        PurchaseOrderItem(
            order_id=purchase.id,
            product_id=product.id,
            variant_id=variant.id if variant else None,
            product_name=item.product_name,
            variant_name=item.variant_name,
            quantity=item.quantity,
            received_quantity=item.quantity if status == "已入库" else 0,
            unit=item.unit,
            unit_price=max(float(item.unit_price or 0) * 0.55, 1),
            notes="状态测试采购明细",
        ),
    )
    return purchase


def add_outbound(db, order, handler, product, variant, status):
    item = db.scalar(select(BusinessOrderItem).where(BusinessOrderItem.order_id == order.id))
    outbound = add(
        db,
        OutboundOrder(
            order_no=f"CK-{order.order_no}",
            outbound_type=order.order_type.replace("订单", "出库"),
            project_name=order.project_name,
            handler=handler.name,
            outbound_date=TODAY,
            status=status,
            notes=f"状态测试出库，来源订单 {order.order_no}",
        ),
    )
    add(
        db,
        OutboundOrderItem(
            order_id=outbound.id,
            product_id=product.id,
            variant_id=variant.id if variant else None,
            product_name=item.product_name,
            variant_name=item.variant_name,
            quantity=item.quantity,
            unit=item.unit,
            unit_price=max(float(item.unit_price or 0) * 0.55, 1),
            notes="状态测试出库明细",
        ),
    )
    return outbound


def add_schedule(db, order, driver, assistant, vehicle, status, source_no=None):
    add(
        db,
        ScheduleTask(
            task_no=f"RC-{source_no or order.order_no}",
            schedule_date=TODAY + timedelta(days=1),
            task_type="配送",
            source_type="订单" if not source_no else "出库单",
            source_no=source_no or order.order_no,
            project_name=order.project_name,
            address="状态测试地址",
            driver_id=driver.id if driver else None,
            assistant_ids=str(assistant.id) if assistant else "",
            vehicle_id=vehicle.id if vehicle else None,
            planned_start="09:00",
            planned_end="11:00",
            item_summary="状态测试配送清单",
            status=status,
            notes="状态测试配送安排",
        ),
    )


def seed():
    Base.metadata.create_all(engine)
    upgrade_legacy_sqlite(engine)
    with SessionLocal() as db:
        cleanup(db)
        employee, purchaser, driver, assistant, vehicle, customer, project, product, variant = ensure_fixture(db)
        cases = [
            ("ZT000001", "租赁订单", "待处理", None, None, None),
            ("ZT000002", "换花订单", "待审批", "approval", None, None),
            ("ZT000003", "销售订单", "待采购", "purchase", "待采购", None),
            ("ZT000004", "换花订单", "待入库", "purchase", "待入库", None),
            ("ZT000005", "租赁订单", "待配送", "purchase", "已入库", None),
            ("ZT000006", "赠送单", "待配送", "outbound", "已入库", "待配送"),
            ("ZT000007", "配送订单", "待配送", "outbound_schedule", "已入库", "已出库"),
            ("ZT000008", "配送订单", "配送中", "schedule", "已入库", "已出库"),
            ("ZT000009", "配送订单", "已完成", "schedule_done", "已入库", "已出库"),
            ("ZT000010", "撤花单", "已取消", None, None, None),
        ]
        for idx, (no, order_type, status, flow, purchase_status, outbound_status) in enumerate(cases, start=1):
            order = make_order(db, no, order_type, status, project, customer, employee, product, variant, idx, need_purchase=flow in {"purchase", "outbound", "outbound_schedule", "schedule", "schedule_done"}, need_delivery=flow not in {"approval"})
            if flow == "approval":
                add(db, ApprovalRequest(request_no=f"SP-{order.order_no}", approval_type="订单审批", source_type="订单", source_id=order.id, source_no=order.order_no, project_id=project.id, project_name=project.name, applicant=order.requester, amount=280, reason="状态测试待审批", approver_role="经理", approver_name=employee.name, status="待审批"))
            if purchase_status:
                add_purchase(db, order, purchaser, product, variant, purchase_status)
            outbound = None
            if outbound_status:
                outbound = add_outbound(db, order, employee, product, variant, outbound_status)
            if flow == "outbound_schedule" and outbound:
                add_schedule(db, order, driver, assistant, vehicle, "待发布", source_no=outbound.order_no)
            if flow == "schedule" and outbound:
                add_schedule(db, order, driver, assistant, vehicle, "配送中", source_no=outbound.order_no)
            if flow == "schedule_done" and outbound:
                add_schedule(db, order, driver, assistant, vehicle, "已完成", source_no=outbound.order_no)
        db.commit()
        print("已生成 10 条订单状态测试数据：ZT000001 - ZT000010")


if __name__ == "__main__":
    seed()
