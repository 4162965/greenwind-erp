from __future__ import annotations

import json
from datetime import date, timedelta
from urllib.parse import quote

from sqlalchemy import and_, select

from app.database import Base, SessionLocal, engine
from app.migrations import upgrade_legacy_sqlite
from app.models import (
    ApprovalRequest,
    ApprovalRule,
    BusinessOrder,
    BusinessOrderItem,
    Contract,
    Customer,
    Employee,
    InventoryMovement,
    InvoiceRecord,
    OutboundOrder,
    OutboundOrderItem,
    Product,
    ProductVariant,
    Project,
    ProjectContact,
    ProjectExpense,
    ProjectLocation,
    ProjectMaintainer,
    ProjectPlant,
    ProjectSalary,
    PurchaseOrder,
    PurchaseOrderItem,
    ReceivableRecord,
    ReceiptRecord,
    ScheduleTask,
    User,
    Vehicle,
)
from app.security import hash_password


TODAY = date.today()


def demo_image(title: str, subtitle: str, bg: str, fg: str = "#166534") -> str:
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="720" height="540" viewBox="0 0 720 540">
      <defs>
        <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="{bg}"/>
          <stop offset="1" stop-color="#f8faf9"/>
        </linearGradient>
      </defs>
      <rect width="720" height="540" rx="32" fill="url(#g)"/>
      <circle cx="580" cy="92" r="96" fill="#ffffff" opacity=".45"/>
      <circle cx="112" cy="455" r="120" fill="#ffffff" opacity=".35"/>
      <path d="M250 335 C250 250 310 210 360 265 C410 210 470 250 470 335 C470 410 250 410 250 335Z" fill="{fg}" opacity=".88"/>
      <path d="M355 340 C345 260 350 210 365 165" stroke="#7c5f36" stroke-width="18" stroke-linecap="round"/>
      <ellipse cx="360" cy="408" rx="145" ry="38" fill="#9a6a38" opacity=".95"/>
      <rect x="250" y="355" width="220" height="85" rx="20" fill="#c58b55"/>
      <text x="48" y="76" font-size="34" font-family="Microsoft YaHei,Arial" font-weight="700" fill="#143c2a">{title}</text>
      <text x="48" y="122" font-size="22" font-family="Microsoft YaHei,Arial" fill="#536159">{subtitle}</text>
      <text x="48" y="490" font-size="18" font-family="Microsoft YaHei,Arial" fill="#6b7a72">绿风管理软件 · 演示图片</text>
    </svg>
    """
    return "data:image/svg+xml;charset=utf-8," + quote(svg.strip())


IMAGES = {
    "pothos": demo_image("小绿萝", "180# / 350# 多规格", "#dff6e8"),
    "fortune": demo_image("单杆发财树", "16分 / 14分", "#e9f6df"),
    "happy": demo_image("幸福树", "1.6-1.8m 大型植物", "#e1f2f7"),
    "pot": demo_image("福字套盆", "大号 / 中号 / 小号", "#f7eadc", "#b26a2c"),
    "pesticide": demo_image("杀虫药", "500ml 养护耗材", "#edf0ff", "#3652a3"),
}


def image_list(value: str) -> str:
    return json.dumps([value], ensure_ascii=False)


def one(db, model, **filters):
    query = select(model)
    for key, value in filters.items():
        query = query.where(getattr(model, key) == value)
    return db.scalar(query)


def ensure(db, model, defaults: dict | None = None, **filters):
    item = one(db, model, **filters)
    values = {**filters, **(defaults or {})}
    if item:
        for key, value in values.items():
            setattr(item, key, value)
        return item
    item = model(**values)
    db.add(item)
    db.flush()
    return item


ROLE_PERMISSIONS = {
    "经理": "dashboard,goods,orders,customers,projects,purchase_inventory,finance,reports,staff,vehicle,schedule_workflow,system",
    "主管": "dashboard,goods,orders,customers,projects,purchase_inventory,reports,vehicle,schedule_workflow",
    "客服": "dashboard,goods,orders,customers,projects,purchase_inventory,finance,vehicle,schedule_workflow",
    "采购": "dashboard,goods,purchase_inventory",
    "仓管": "dashboard,goods,purchase_inventory,schedule_workflow",
    "财务": "dashboard,finance,reports,projects",
    "养护员": "dashboard,orders,projects,schedule_workflow",
    "司机": "dashboard,vehicle,schedule_workflow",
    "跟车配送": "dashboard,schedule_workflow",
}


def default_permissions(role: str) -> str:
    for key, value in ROLE_PERMISSIONS.items():
        if key in role:
            return value
    return "dashboard"


def ensure_user(db, username: str, display_name: str, role: str = "员工", password: str = "123456", module_permissions: str = ""):
    user = one(db, User, username=username)
    if user:
        user.display_name = display_name
        user.role = role
        user.module_permissions = module_permissions or default_permissions(role)
        user.is_active = True
        return user
    user = User(username=username, display_name=display_name, role=role, module_permissions=module_permissions or default_permissions(role), password_hash=hash_password(password), is_active=True)
    db.add(user)
    db.flush()
    return user


def ensure_employee(db, phone: str, name: str, position: str, role: str, department: str, business_roles: str = ""):
    permissions = default_permissions(role or position)
    employee = ensure(
        db,
        Employee,
        phone=phone,
        defaults={
            "name": name,
            "position": position,
            "role": role,
            "department": department,
            "business_roles": business_roles or role,
            "module_permissions": permissions,
            "hire_date": date(2024, 1, 1),
            "login_enabled": True,
            "status": "在职",
            "responsibility": "演示数据：用于测试权限、派单和业务流程。",
        },
    )
    ensure_user(db, phone, name, role, module_permissions=permissions)
    return employee


def ensure_variant(db, product: Product, code: str, specification: str, unit: str, stock: float, purchase: float, sale: float, rent: float, sort: int):
    return ensure(
        db,
        ProductVariant,
        code=code,
        defaults={
            "product_id": product.id,
            "specification": specification,
            "specification_values": specification,
            "unit": unit,
            "stock": stock,
            "reference_purchase_price": purchase,
            "sale_price": sale,
            "monthly_rental_price": rent,
            "sort_order": sort,
            "is_default": sort == 1,
            "status": "启用",
        },
    )


def ensure_location(db, project: Project, name: str, location_type: str, parent_id: int | None = None, sort: int = 0):
    item = db.scalar(
        select(ProjectLocation).where(
            and_(
                ProjectLocation.project_id == project.id,
                ProjectLocation.parent_id == parent_id,
                ProjectLocation.name == name,
                ProjectLocation.location_type == location_type,
            )
        )
    )
    if item:
        item.sort_order = sort
        return item
    item = ProjectLocation(project_id=project.id, parent_id=parent_id, name=name, location_type=location_type, sort_order=sort)
    db.add(item)
    db.flush()
    return item


def main():
    Base.metadata.create_all(engine)
    upgrade_legacy_sqlite(engine)
    with SessionLocal() as db:
        manager = ensure_employee(db, "13800000001", "演示-李经理", "经理", "经理", "管理层", "审批,项目统筹")
        supervisor = ensure_employee(db, "13800000002", "演示-王主管", "区域主管", "主管", "绿化部", "项目管理,换花审批")
        service = ensure_employee(db, "13800000003", "演示-陈客服", "客服", "客服", "客服部", "接单,派单")
        buyer = ensure_employee(db, "13800000004", "演示-赵采购", "采购员", "采购", "采购部", "采购")
        warehouse = ensure_employee(db, "13800000005", "演示-钱仓管", "仓管", "仓管", "仓管部", "入库,出库")
        finance = ensure_employee(db, "13800000006", "演示-孙财务", "财务", "财务", "财务部", "开票,收款")
        maintainer_a = ensure_employee(db, "13800000007", "演示-周养护", "养护员", "养护员", "绿化部", "养护,报换花")
        maintainer_b = ensure_employee(db, "13800000008", "演示-吴养护", "养护员", "养护员", "绿化部", "养护,报换花")
        driver = ensure_employee(db, "13800000009", "演示-郑司机", "司机", "司机", "配送部", "配送")
        assistant = ensure_employee(db, "13800000010", "演示-冯跟车", "跟车配送", "跟车配送", "配送部", "配送")

        green_pothos = ensure(
            db,
            Product,
            code="DEMO-P-001",
            defaults={
                "name": "演示-小绿萝",
                "category": "植物",
                "specification": "多规格",
                "unit": "盆",
                "purchase_unit": "盆",
                "base_unit": "盆",
                "project_unit": "盆",
                "stock": 36,
                "reference_purchase_price": 3.8,
                "sale_price": 8,
                "monthly_rental_price": 1.5,
                "image_url": IMAGES["pothos"],
                "image_urls": image_list(IMAGES["pothos"]),
                "status": "启用",
            },
        )
        pothos_180 = ensure_variant(db, green_pothos, "DEMO-P-001-180", "180#", "盆", 24, 3.8, 8, 1.5, 1)
        pothos_180.image_url = IMAGES["pothos"]
        pothos_350 = ensure_variant(db, green_pothos, "DEMO-P-001-350", "350#", "盆", 12, 6.5, 15, 2.5, 2)
        pothos_350.image_url = IMAGES["pothos"]

        fortune_tree = ensure(
            db,
            Product,
            code="DEMO-P-002",
            defaults={
                "name": "演示-单杆发财树",
                "category": "植物",
                "specification": "青龙盆/紫砂盆多规格",
                "unit": "盆",
                "purchase_unit": "盆",
                "base_unit": "盆",
                "project_unit": "盆",
                "stock": 8,
                "reference_purchase_price": 120,
                "sale_price": 280,
                "monthly_rental_price": 35,
                "image_url": IMAGES["fortune"],
                "image_urls": image_list(IMAGES["fortune"]),
                "status": "启用",
            },
        )
        fortune_16 = ensure_variant(db, fortune_tree, "DEMO-P-002-16", "16分", "盆", 5, 120, 280, 35, 1)
        fortune_16.image_url = IMAGES["fortune"]
        fortune_14 = ensure_variant(db, fortune_tree, "DEMO-P-002-14", "14分", "盆", 3, 95, 220, 28, 2)
        fortune_14.image_url = IMAGES["fortune"]

        happy_tree = ensure(
            db,
            Product,
            code="DEMO-P-003",
            defaults={
                "name": "演示-幸福树",
                "category": "植物",
                "specification": "1.6-1.8m",
                "unit": "盆",
                "purchase_unit": "盆",
                "base_unit": "盆",
                "project_unit": "盆",
                "stock": 6,
                "reference_purchase_price": 160,
                "sale_price": 360,
                "monthly_rental_price": 45,
                "image_url": IMAGES["happy"],
                "image_urls": image_list(IMAGES["happy"]),
                "status": "启用",
            },
        )
        happy_18 = ensure_variant(db, happy_tree, "DEMO-P-003-18", "1.8米", "盆", 6, 160, 360, 45, 1)
        happy_18.image_url = IMAGES["happy"]

        pot_set = ensure(
            db,
            Product,
            code="DEMO-P-004",
            defaults={
                "name": "演示-福字套盆",
                "category": "花盆",
                "specification": "大中小成套采购",
                "unit": "套",
                "purchase_unit": "套",
                "base_unit": "套",
                "project_unit": "个",
                "stock": 10,
                "reference_purchase_price": 55,
                "package_conversion_enabled": True,
                "image_url": IMAGES["pot"],
                "image_urls": image_list(IMAGES["pot"]),
                "status": "启用",
            },
        )
        pot_big = ensure_variant(db, pot_set, "DEMO-P-004-L", "大号", "个", 10, 24, 45, 0, 1)
        pot_big.image_url = IMAGES["pot"]
        pot_mid = ensure_variant(db, pot_set, "DEMO-P-004-M", "中号", "个", 10, 18, 35, 0, 2)
        pot_mid.image_url = IMAGES["pot"]
        pot_small = ensure_variant(db, pot_set, "DEMO-P-004-S", "小号", "个", 10, 13, 25, 0, 3)
        pot_small.image_url = IMAGES["pot"]

        pesticide = ensure(
            db,
            Product,
            code="DEMO-P-005",
            defaults={
                "name": "演示-杀虫药",
                "category": "农药",
                "specification": "500ml",
                "unit": "瓶",
                "purchase_unit": "瓶",
                "base_unit": "瓶",
                "project_unit": "瓶",
                "stock": 20,
                "reference_purchase_price": 18,
                "sale_price": 28,
                "image_url": IMAGES["pesticide"],
                "image_urls": image_list(IMAGES["pesticide"]),
                "status": "启用",
            },
        )
        pesticide_v = ensure_variant(db, pesticide, "DEMO-P-005-500", "500ml", "瓶", 20, 18, 28, 0, 1)
        pesticide_v.image_url = IMAGES["pesticide"]

        customer_a = ensure(
            db,
            Customer,
            name="演示-金融中心物业",
            defaults={"customer_type": "企业客户", "contact_person": "刘主任", "phone": "13900001001", "address": "金融大道1号", "status": "启用"},
        )
        customer_b = ensure(
            db,
            Customer,
            name="演示-科技园管理处",
            defaults={"customer_type": "企业客户", "contact_person": "黄经理", "phone": "13900001002", "address": "科技园A区", "status": "启用"},
        )
        customer_c = ensure(
            db,
            Customer,
            name="演示-临时销售客户",
            defaults={"customer_type": "个人客户", "contact_person": "林小姐", "phone": "13900001003", "address": "南山办公室", "status": "启用"},
        )

        project_a = ensure(
            db,
            Project,
            code="DEMO-PRJ-001",
            defaults={
                "customer_id": customer_a.id,
                "name": "演示-金融中心租摆项目",
                "address": "金融大道1号",
                "business_types": "租摆,室外养护,临时销售",
                "plant_source": "新采购",
                "supervisor_id": supervisor.id,
                "customer_service_id": service.id,
                "start_date": date(2026, 8, 1),
                "status": "进行中",
                "notes": "演示数据：包含租摆、室外养护和临时销售。",
            },
        )
        project_b = ensure(
            db,
            Project,
            code="DEMO-PRJ-002",
            defaults={
                "customer_id": customer_b.id,
                "name": "演示-科技园室外养护项目",
                "address": "科技园A区",
                "business_types": "室外养护",
                "plant_source": "买断原场",
                "supervisor_id": supervisor.id,
                "customer_service_id": service.id,
                "start_date": date(2026, 7, 1),
                "status": "进行中",
            },
        )
        project_c = ensure(
            db,
            Project,
            code="DEMO-PRJ-003",
            defaults={
                "customer_id": customer_c.id,
                "name": "演示-临时销售项目",
                "address": "南山办公室",
                "business_types": "临时销售",
                "plant_source": "新采购",
                "supervisor_id": supervisor.id,
                "customer_service_id": service.id,
                "start_date": TODAY,
                "status": "进行中",
            },
        )

        for project, contact_name, phone in [(project_a, "刘主任", "13900001001"), (project_a, "销售跟进-何小姐", "13900001004"), (project_b, "黄经理", "13900001002"), (project_c, "林小姐", "13900001003")]:
            contact = db.scalar(select(ProjectContact).where(and_(ProjectContact.project_id == project.id, ProjectContact.name == contact_name)))
            if not contact:
                db.add(ProjectContact(project_id=project.id, name=contact_name, phone=phone, position="项目联系人", contact_type="项目负责人", priority=1))

        ensure(db, ProjectMaintainer, project_id=project_a.id, employee_id=maintainer_a.id, defaults={"area_description": "8楼总经理办公室、前台", "is_primary": True, "start_date": date(2026, 8, 1), "status": "负责中"})
        ensure(db, ProjectMaintainer, project_id=project_a.id, employee_id=maintainer_b.id, defaults={"area_description": "9楼会议区", "is_primary": False, "start_date": date(2026, 8, 1), "status": "负责中"})
        ensure(db, ProjectMaintainer, project_id=project_b.id, employee_id=maintainer_b.id, defaults={"area_description": "园区室外绿化", "is_primary": True, "start_date": date(2026, 7, 1), "status": "负责中"})

        floor_8 = ensure_location(db, project_a, "8楼", "楼层", sort=1)
        office_gm = ensure_location(db, project_a, "总经理办公室", "区域", parent_id=floor_8.id, sort=1)
        front_desk = ensure_location(db, project_a, "前台", "区域", parent_id=floor_8.id, sort=2)
        floor_9 = ensure_location(db, project_a, "9楼", "楼层", sort=2)
        meeting = ensure_location(db, project_a, "会议区", "区域", parent_id=floor_9.id, sort=1)
        outdoor = ensure_location(db, project_b, "室外园区", "区域", sort=1)

        ensure(db, ProjectPlant, project_id=project_a.id, location_id=office_gm.id, product_id=happy_tree.id, defaults={"specification": "1.8米", "quantity": 1, "unit": "盆", "decorative_pot": "福字盆中号", "source": "新采购", "maintainer_id": maintainer_a.id, "entry_date": date(2026, 8, 2), "billing_start_date": date(2026, 8, 5), "status": "在场"})
        ensure(db, ProjectPlant, project_id=project_a.id, location_id=front_desk.id, product_id=green_pothos.id, defaults={"specification": "180#", "quantity": 10, "unit": "盆", "decorative_pot": "白色瓷盆", "source": "新采购", "maintainer_id": maintainer_a.id, "entry_date": date(2026, 8, 2), "billing_start_date": date(2026, 8, 5), "status": "在场"})
        ensure(db, ProjectPlant, project_id=project_a.id, location_id=meeting.id, product_id=fortune_tree.id, defaults={"specification": "16分", "quantity": 2, "unit": "盆", "decorative_pot": "青龙盆", "source": "新采购", "maintainer_id": maintainer_b.id, "entry_date": date(2026, 8, 2), "billing_start_date": date(2026, 8, 5), "status": "在场"})
        ensure(db, ProjectPlant, project_id=project_b.id, location_id=outdoor.id, product_id=pesticide.id, defaults={"specification": "500ml", "quantity": 3, "unit": "瓶", "source": "养护耗材", "maintainer_id": maintainer_b.id, "entry_date": date(2026, 8, 3), "billing_start_date": date(2026, 8, 3), "status": "在场"})

        contract_a = ensure(
            db,
            Contract,
            contract_no="DEMO-HT-001",
            defaults={"project_id": project_a.id, "name": "演示-金融中心租摆整体合同", "contract_type": "整体合同", "business_types": "租摆,室外养护", "effective_date": date(2026, 8, 1), "end_date": date(2027, 7, 31), "billing_start_date": date(2026, 8, 5), "billing_cycle": "月付", "amount": 6800, "reminder_days": 45, "status": "生效"},
        )
        contract_b = ensure(
            db,
            Contract,
            contract_no="DEMO-HT-002",
            defaults={"project_id": project_b.id, "name": "演示-科技园室外养护合同", "contract_type": "分体合同", "business_types": "室外养护", "effective_date": date(2026, 7, 1), "end_date": date(2027, 6, 30), "billing_start_date": date(2026, 7, 1), "billing_cycle": "月付", "amount": 4200, "reminder_days": 30, "status": "生效"},
        )

        ensure(db, ApprovalRule, project_id=project_a.id, defaults={"purchase_requires_approval": True, "exchange_annual_limit": 300, "approver_role": "经理", "approver_name": manager.name, "status": "启用"})
        ensure(db, ApprovalRule, project_id=project_b.id, defaults={"purchase_requires_approval": False, "exchange_annual_limit": 500, "approver_role": "主管", "approver_name": supervisor.name, "status": "启用"})

        purchase_1 = ensure(db, PurchaseOrder, order_no="DEMO-CG-001", defaults={"supplier": "演示-花场供应商", "purchaser": buyer.name, "purchase_date": date(2026, 8, 2), "delivery_method": "入库", "freight_fee": 80, "hll_fee": 0, "status": "已入库", "notes": "金融中心进场植物采购"})
        purchase_2 = ensure(db, PurchaseOrder, order_no="DEMO-CG-002", defaults={"supplier": "演示-花盆供应商", "purchaser": buyer.name, "purchase_date": date(2026, 8, 8), "delivery_method": "货拉拉", "freight_fee": 0, "hll_fee": 60, "status": "待入库", "notes": "换花需要的福字套盆"})
        purchase_3 = ensure(db, PurchaseOrder, order_no="DEMO-CG-003", defaults={"supplier": "演示-农资店", "purchaser": buyer.name, "purchase_date": date(2026, 8, 9), "delivery_method": "快递", "freight_fee": 15, "hll_fee": 0, "status": "待采购", "notes": "室外养护打药耗材"})

        purchase_items = [
            (purchase_1, green_pothos, pothos_180, 24, 24, "盆", 3.8),
            (purchase_1, fortune_tree, fortune_16, 2, 2, "盆", 120),
            (purchase_1, happy_tree, happy_18, 1, 1, "盆", 160),
            (purchase_2, pot_set, pot_big, 3, 0, "个", 24),
            (purchase_2, pot_set, pot_mid, 3, 0, "个", 18),
            (purchase_2, pot_set, pot_small, 3, 0, "个", 13),
            (purchase_3, pesticide, pesticide_v, 5, 0, "瓶", 18),
        ]
        for order, product, variant, qty, received, unit, price in purchase_items:
            existing = db.scalar(select(PurchaseOrderItem).where(and_(PurchaseOrderItem.order_id == order.id, PurchaseOrderItem.product_id == product.id, PurchaseOrderItem.variant_id == variant.id)))
            if not existing:
                db.add(PurchaseOrderItem(order_id=order.id, product_id=product.id, variant_id=variant.id, product_name=product.name, variant_name=variant.specification, quantity=qty, received_quantity=received, unit=unit, unit_price=price))

        for product, variant, qty, price, no in [(green_pothos, pothos_180, 24, 3.8, "DEMO-RK-001"), (fortune_tree, fortune_16, 2, 120, "DEMO-RK-002"), (happy_tree, happy_18, 1, 160, "DEMO-RK-003")]:
            if not db.scalar(select(InventoryMovement).where(and_(InventoryMovement.source_no == no, InventoryMovement.product_id == product.id))):
                db.add(InventoryMovement(product_id=product.id, variant_id=variant.id, product_name=product.name, variant_name=variant.specification, movement_type="采购入库", direction="入库", quantity=qty, before_stock=0, after_stock=qty, unit=variant.unit, unit_price=price, total_amount=qty * price, source_type="采购单", source_no=no, operator=warehouse.name, notes="演示采购入库"))

        outbound = ensure(db, OutboundOrder, order_no="DEMO-CK-001", defaults={"outbound_type": "项目领用", "project_name": project_a.name, "handler": service.name, "outbound_date": date(2026, 8, 10), "status": "已出库", "notes": "金融中心进场配送出库"})
        for product, variant, qty, price in [(happy_tree, happy_18, 1, 160), (green_pothos, pothos_180, 10, 3.8), (fortune_tree, fortune_16, 2, 120)]:
            if not db.scalar(select(OutboundOrderItem).where(and_(OutboundOrderItem.order_id == outbound.id, OutboundOrderItem.product_id == product.id, OutboundOrderItem.variant_id == variant.id))):
                db.add(OutboundOrderItem(order_id=outbound.id, product_id=product.id, variant_id=variant.id, product_name=product.name, variant_name=variant.specification, quantity=qty, unit=variant.unit, unit_price=price, notes="演示出库"))

        orders = [
            ("DEMO-DD-001", "租摆订单", project_a, customer_a.name, service.name, "已完成", True, True, "金融中心进场租摆：幸福树1盆、小绿萝10盆、发财树2盆"),
            ("DEMO-DD-002", "换花单", project_a, customer_a.name, maintainer_a.name, "待审批", True, True, "8楼前台小绿萝状态差，需要换5盆"),
            ("DEMO-DD-003", "撤花单", project_a, customer_a.name, supervisor.name, "待处理", False, True, "9楼会议区撤发财树1盆，默认丢弃"),
            ("DEMO-DD-004", "销售订单", project_c, customer_c.name, service.name, "配送中", True, True, "临时销售幸福树1盆，货拉拉直送"),
            ("DEMO-DD-005", "养护工程订单", project_b, customer_b.name, maintainer_b.name, "已完成", False, False, "室外园区修剪打药，客户现场处理"),
        ]
        order_objs = {}
        for no, order_type, project, customer_name, requester, status_text, need_purchase, need_delivery, notes in orders:
            order = ensure(
                db,
                BusinessOrder,
                order_no=no,
                defaults={
                    "order_type": order_type,
                    "project_id": project.id,
                    "project_name": project.name,
                    "customer_name": customer_name,
                    "requester": requester,
                    "contact_phone": "13900001001",
                    "order_date": date(2026, 8, 9),
                    "expected_date": date(2026, 8, 10),
                    "priority": "普通" if no != "DEMO-DD-002" else "紧急",
                    "need_purchase": need_purchase,
                    "need_delivery": need_delivery,
                    "status": status_text,
                    "notes": notes,
                },
            )
            order_objs[no] = order

        order_items = [
            ("DEMO-DD-001", happy_tree, happy_18, "8楼 总经理办公室", 1, "盆", 45),
            ("DEMO-DD-001", green_pothos, pothos_180, "8楼 前台", 10, "盆", 1.5),
            ("DEMO-DD-002", green_pothos, pothos_180, "8楼 前台", 5, "盆", 3.8),
            ("DEMO-DD-003", fortune_tree, fortune_16, "9楼 会议区", 1, "盆", 0),
            ("DEMO-DD-004", happy_tree, happy_18, "客户自选", 1, "盆", 360),
            ("DEMO-DD-005", pesticide, pesticide_v, "室外园区", 2, "瓶", 18),
        ]
        for order_no, product, variant, location, qty, unit, price in order_items:
            order = order_objs[order_no]
            if not db.scalar(select(BusinessOrderItem).where(and_(BusinessOrderItem.order_id == order.id, BusinessOrderItem.product_id == product.id, BusinessOrderItem.variant_id == variant.id, BusinessOrderItem.location_text == location))):
                db.add(BusinessOrderItem(order_id=order.id, product_id=product.id, variant_id=variant.id, product_name=product.name, variant_name=variant.specification, location_text=location, quantity=qty, unit=unit, unit_price=price, amount=qty * price))

        ensure(db, ApprovalRequest, request_no="DEMO-SP-001", defaults={"approval_type": "换花超额审批", "source_type": "订单", "source_id": order_objs["DEMO-DD-002"].id, "source_no": "DEMO-DD-002", "project_id": project_a.id, "project_name": project_a.name, "applicant": maintainer_a.name, "amount": 320, "reason": "演示：项目年度换花累计超过设定值，需经理审批。", "approver_role": "经理", "approver_name": manager.name, "status": "待审批"})

        vehicle_1 = ensure(db, Vehicle, plate_no="粤B-DEMO1", defaults={"vehicle_type": "面包车", "driver_name": driver.name, "status": "可用", "insurance_expiry": TODAY + timedelta(days=20), "inspection_expiry": TODAY + timedelta(days=120), "maintenance_due_date": TODAY + timedelta(days=15), "reminder_days": 30, "reminder_to": "演示-陈客服、演示-王主管", "notes": "演示车辆：即将到期提醒"})
        vehicle_2 = ensure(db, Vehicle, plate_no="粤B-DEMO2", defaults={"vehicle_type": "小货车", "driver_name": "", "status": "维修中", "insurance_expiry": TODAY - timedelta(days=3), "inspection_expiry": TODAY + timedelta(days=60), "maintenance_due_date": TODAY + timedelta(days=90), "reminder_days": 30, "reminder_to": "演示-王主管", "notes": "演示车辆：保险已过期"})
        ensure(db, Vehicle, plate_no="粤B-DEMO3", defaults={"vehicle_type": "货拉拉外协", "driver_name": "外协司机", "status": "可用", "insurance_expiry": TODAY + timedelta(days=180), "inspection_expiry": TODAY + timedelta(days=180), "maintenance_due_date": TODAY + timedelta(days=180), "reminder_days": 30, "reminder_to": "演示-陈客服", "notes": "演示车辆：外协/货拉拉场景"})

        schedules = [
            ("DEMO-RC-001", date(2026, 8, 10), "配送", "出库单", "DEMO-CK-001", project_a.name, project_a.address, driver.id, str(assistant.id), vehicle_1.id, "09:00", "11:30", "幸福树×1盆；小绿萝×10盆；发财树×2盆", "已完成"),
            ("DEMO-RC-002", TODAY + timedelta(days=1), "换花", "订单", "DEMO-DD-002", project_a.name, project_a.address, driver.id, str(assistant.id), vehicle_1.id, "10:00", "12:00", "8楼前台小绿萝×5盆", "待发布"),
            ("DEMO-RC-003", TODAY + timedelta(days=1), "修剪打药", "订单", "DEMO-DD-005", project_b.name, project_b.address, maintainer_b.id, "", None, "14:00", "16:00", "室外园区修剪、打药", "已发布"),
        ]
        for no, schedule_date, task_type, source_type, source_no, project_name, address, driver_id, assistant_ids, vehicle_id, start, end, summary, status_text in schedules:
            ensure(db, ScheduleTask, task_no=no, defaults={"schedule_date": schedule_date, "task_type": task_type, "source_type": source_type, "source_no": source_no, "project_name": project_name, "address": address, "driver_id": driver_id, "assistant_ids": assistant_ids, "vehicle_id": vehicle_id, "planned_start": start, "planned_end": end, "item_summary": summary, "status": status_text, "notes": "演示每日安排"})

        ensure(db, ProjectSalary, project_id=project_a.id, employee_id=maintainer_a.id, salary_month="2026-08", defaults={"amount": 1800, "adjustment_reason": "金融中心8楼养护工资", "status": "已确认"})
        ensure(db, ProjectSalary, project_id=project_a.id, employee_id=maintainer_b.id, salary_month="2026-08", defaults={"amount": 900, "adjustment_reason": "金融中心9楼养护工资", "status": "已确认"})
        ensure(db, ProjectSalary, project_id=project_b.id, employee_id=maintainer_b.id, salary_month="2026-08", defaults={"amount": 2200, "adjustment_reason": "科技园室外养护工资", "status": "已确认"})
        ensure(db, ProjectExpense, project_id=project_a.id, expense_date=date(2026, 8, 8), defaults={"expense_type": "货拉拉", "amount": 60, "handler": service.name, "source_no": "DEMO-CG-002", "description": "换花套盆货拉拉费用", "status": "已确认"})
        ensure(db, ProjectExpense, project_id=project_b.id, expense_date=date(2026, 8, 9), defaults={"expense_type": "临工", "amount": 300, "handler": supervisor.name, "source_no": "DEMO-LG-001", "description": "室外修剪临工费用", "status": "已确认"})

        receivable_1 = ensure(db, ReceivableRecord, receivable_no="DEMO-YS-001", defaults={"project_id": project_a.id, "contract_id": contract_a.id, "billing_period": "2026-08", "due_date": date(2026, 8, 31), "amount": 6800, "invoice_amount": 6800, "received_amount": 3000, "receivable_type": "合同应收", "status": "部分收款", "notes": "金融中心8月租摆应收"})
        ensure(db, ReceivableRecord, receivable_no="DEMO-YS-002", defaults={"project_id": project_b.id, "contract_id": contract_b.id, "billing_period": "2026-08", "due_date": date(2026, 8, 31), "amount": 4200, "invoice_amount": 0, "received_amount": 0, "receivable_type": "合同应收", "status": "待收款", "notes": "科技园8月养护应收"})
        invoice = ensure(db, InvoiceRecord, invoice_no="DEMO-FP-001", defaults={"project_id": project_a.id, "contract_id": contract_a.id, "invoice_date": date(2026, 8, 15), "billing_period": "2026-08", "amount": 6800, "tax_amount": 0, "invoice_type": "增值税普通发票", "payer_name": customer_a.name, "handler": finance.name, "source_no": receivable_1.receivable_no, "status": "已开票", "notes": "演示开票"})
        ensure(db, ReceiptRecord, receipt_no="DEMO-SK-001", defaults={"project_id": project_a.id, "contract_id": contract_a.id, "invoice_id": invoice.id, "receipt_date": date(2026, 8, 20), "billing_period": "2026-08", "amount": 3000, "payment_method": "银行转账", "payer_name": customer_a.name, "handler": finance.name, "source_no": invoice.invoice_no, "status": "已收款", "notes": "演示部分收款"})

        fallback_by_category = {
            "植物": IMAGES["pothos"],
            "花盆": IMAGES["pot"],
            "农药": IMAGES["pesticide"],
            "肥料": IMAGES["pesticide"],
        }
        for product in db.scalars(select(Product)).all():
            if product.image_url:
                continue
            fallback = fallback_by_category.get(product.category or "", demo_image(product.name or "商品", product.category or "通用商品", "#eef5f0"))
            product.image_url = fallback
            product.image_urls = image_list(fallback)
        for variant in db.scalars(select(ProductVariant)).all():
            if variant.image_url:
                continue
            product = db.get(Product, variant.product_id)
            if product and product.image_url:
                variant.image_url = product.image_url

        db.commit()

        counts = {
            "employees": db.scalar(select(Employee).where(Employee.name.like("演示-%")).count()) if False else len(db.scalars(select(Employee).where(Employee.name.like("演示-%"))).all()),
            "products": len(db.scalars(select(Product).where(Product.code.like("DEMO-%"))).all()),
            "projects": len(db.scalars(select(Project).where(Project.code.like("DEMO-%"))).all()),
            "orders": len(db.scalars(select(BusinessOrder).where(BusinessOrder.order_no.like("DEMO-%"))).all()),
            "vehicles": len(db.scalars(select(Vehicle).where(Vehicle.plate_no.like("%DEMO%"))).all()),
        }
        print("演示测试数据已写入：")
        for key, value in counts.items():
            print(f"- {key}: {value}")
        print("演示员工登录账号为手机号，密码均为 123456。")


if __name__ == "__main__":
    main()
