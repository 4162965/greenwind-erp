from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import delete, select, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, SessionLocal, engine
from app.migrations import upgrade_legacy_sqlite
from app.models import (
    ApprovalRequest,
    ApprovalRule,
    Attachment,
    BusinessOrder,
    BusinessOrderItem,
    Contract,
    Customer,
    CustomerAreaSetting,
    Employee,
    InventoryMovement,
    InvoiceRecord,
    MaintenancePlan,
    MaintenanceRecord,
    OperationLog,
    OutboundOrder,
    OutboundOrderItem,
    Product,
    ProductCategory,
    ProductVariant,
    Project,
    ProjectContact,
    ProjectExpense,
    ProjectLocation,
    ProjectMaintainer,
    ProjectPlant,
    ProjectPlantChange,
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


TODAY = date(2026, 8, 12)


def backup_database() -> Path | None:
    db_path = BACKEND_DIR / "greenwind.db"
    if not db_path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = db_path.with_name(f"greenwind.before-real-data-{stamp}.db")
    shutil.copy2(db_path, target)
    return target


def image(title: str, subtitle: str, bg: str, fg: str = "#128a56") -> str:
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="640" height="640" viewBox="0 0 640 640">
      <defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="{bg}"/>
          <stop offset="1" stop-color="#f8fffb"/>
        </linearGradient>
      </defs>
      <rect width="640" height="640" rx="42" fill="url(#bg)"/>
      <circle cx="520" cy="110" r="110" fill="#fff" opacity=".42"/>
      <circle cx="110" cy="545" r="130" fill="#fff" opacity=".36"/>
      <path d="M280 365 C214 286 265 214 330 282 C388 202 468 260 418 366 C386 430 314 430 280 365Z" fill="{fg}" opacity=".9"/>
      <path d="M330 380 C320 300 322 232 345 170" stroke="#7b5830" stroke-width="18" stroke-linecap="round"/>
      <ellipse cx="330" cy="465" rx="132" ry="38" fill="#9a6a38" opacity=".95"/>
      <rect x="220" y="408" width="220" height="96" rx="22" fill="#c68a55"/>
      <text x="42" y="72" font-size="34" font-family="Microsoft YaHei,Arial" font-weight="700" fill="#153728">{title}</text>
      <text x="42" y="118" font-size="21" font-family="Microsoft YaHei,Arial" fill="#5a6c63">{subtitle}</text>
      <text x="42" y="586" font-size="18" font-family="Microsoft YaHei,Arial" fill="#6f7f76">绿风环境花卉 · 真实样例数据</text>
    </svg>
    """
    return "data:image/svg+xml;charset=utf-8," + quote(svg.strip())


def image_list(value: str) -> str:
    return json.dumps([value], ensure_ascii=False)


def add(db, obj):
    db.add(obj)
    db.flush()
    return obj


def permissions(role: str) -> str:
    mapping = {
        "经理": "dashboard,goods,orders,customers,projects,purchase_inventory,finance,reports,staff,vehicle,schedule_workflow,system",
        "主管": "dashboard,goods,orders,customers,projects,purchase_inventory,reports,vehicle,schedule_workflow",
        "客服": "dashboard,goods,orders,customers,projects,purchase_inventory,finance,vehicle,schedule_workflow",
        "采购": "dashboard,goods,purchase_inventory,orders",
        "养护员": "dashboard,orders,projects,schedule_workflow",
    }
    for key, value in mapping.items():
        if key in role:
            return value
    return "dashboard"


def ensure_admin(db) -> User:
    admin = db.scalar(select(User).where(User.username == "admin"))
    if admin:
        admin.display_name = "系统管理员"
        admin.role = "admin"
        admin.module_permissions = permissions("经理")
        admin.is_active = True
        return admin
    return add(
        db,
        User(
            username="admin",
            display_name="系统管理员",
            role="admin",
            module_permissions=permissions("经理"),
            password_hash=hash_password("admin123"),
            is_active=True,
        ),
    )


def clear_business_data(db):
    for model in [
        Attachment,
        OperationLog,
        ApprovalRequest,
        ApprovalRule,
        ScheduleTask,
        ReceiptRecord,
        InvoiceRecord,
        ReceivableRecord,
        ProjectExpense,
        ProjectSalary,
        MaintenanceRecord,
        MaintenancePlan,
    ]:
        db.execute(delete(model))

    for model in [
        BusinessOrderItem,
        BusinessOrder,
        OutboundOrderItem,
        OutboundOrder,
        InventoryMovement,
        PurchaseOrderItem,
        PurchaseOrder,
        ProjectPlantChange,
        ProjectPlant,
        Contract,
        ProjectMaintainer,
        ProjectLocation,
        ProjectContact,
        Project,
        Vehicle,
        CustomerAreaSetting,
        Customer,
        ProductVariant,
        Product,
        ProductCategory,
        Employee,
    ]:
        db.execute(delete(model))

    db.execute(delete(User).where(User.username != "admin"))
    db.flush()


def ensure_legacy_columns(db):
    columns = {row[1] for row in db.execute(text("PRAGMA table_info(product_variants)")).fetchall()}
    if "package_type" not in columns:
        db.execute(text("ALTER TABLE product_variants ADD COLUMN package_type VARCHAR(16) NOT NULL DEFAULT '单品'"))
    if "bundle_components" not in columns:
        db.execute(text("ALTER TABLE product_variants ADD COLUMN bundle_components TEXT NOT NULL DEFAULT ''"))
    db.flush()


def seed_users_employees(db):
    data = [
        ("17688855443", "伍龙辉", "经理", "总经理", "管理层", "审批、经营分析、项目统筹"),
        ("13922233362", "任飞扬", "主管", "区域主管", "绿化部", "A区项目管理、换花审批"),
        ("13620498851", "梁小敏", "客服", "客服", "客服部", "客户接单、派单、回访"),
        ("13570981236", "赵俊杰", "采购", "采购兼仓管", "采购仓管部", "采购、入库、库存盘点"),
        ("13711160028", "周海强", "养护员", "养护员兼司机", "绿化配送部", "项目养护、配送、现场反馈"),
    ]
    employees = {}
    for phone, name, role, position, department, responsibility in data:
        employee = add(
            db,
            Employee(
                name=name,
                phone=phone,
                position=position,
                role=role,
                department=department,
                business_roles=role,
                module_permissions=permissions(role),
                product_category_permissions="植物,花盆,农资,工具",
                hire_date=date(2024, 1, 1),
                login_enabled=True,
                responsibility=responsibility,
                status="在职",
            ),
        )
        add(
            db,
            User(
                username=phone,
                display_name=name,
                role=role,
                module_permissions=permissions(role),
                product_category_permissions="植物,花盆,农资,工具",
                password_hash=hash_password("123456"),
                is_active=True,
            ),
        )
        employees[name] = employee
    return employees


def seed_products(db):
    for index, name in enumerate(["植物", "花盆", "农资", "工具", "组合盆景"], start=1):
        add(db, ProductCategory(name=name, sort_order=index, status="启用"))

    product_specs = [
        ("P-00001", "小绿萝", "植物", "盆", "180#", 3.8, 8, 1.5, 120, image("小绿萝", "180# 桌面绿植", "#dff6e8")),
        ("P-00002", "单杆发财树", "植物", "盆", "高1.6m", 120, 280, 35, 18, image("单杆发财树", "办公室常用租摆", "#e7f4df")),
        ("P-00003", "天堂鸟", "植物", "盆", "高1.8m", 95, 220, 30, 15, image("天堂鸟", "大厅与会客区", "#e1f3f7")),
        ("P-00004", "福字套盆", "花盆", "套", "大中小", 55, 0, 0, 20, image("福字套盆", "成套采购，可拆单出库", "#f8eadb", "#b26a2c")),
        ("P-00005", "杀虫药", "农资", "瓶", "500ml", 18, 28, 0, 36, image("杀虫药", "室外养护耗材", "#edf0ff", "#3652a3")),
    ]
    products = {}
    variants = {}
    for code, name, category, unit, spec, purchase, sale, rent, stock, img in product_specs:
        product = add(
            db,
            Product(
                code=code,
                name=name,
                category=category,
                specification=spec,
                unit=unit,
                purchase_unit=unit,
                base_unit=unit,
                project_unit=unit,
                reference_purchase_price=purchase,
                sale_price=sale,
                monthly_rental_price=rent,
                stock=stock,
                image_url=img,
                image_urls=image_list(img),
                package_conversion_enabled=name == "福字套盆",
                status="启用",
            ),
        )
        if name == "福字套盆":
            parent = add(
                db,
                ProductVariant(
                    product_id=product.id,
                    code=f"{code}-SET",
                    specification="整套",
                    specification_values=json.dumps({"型号": "整套"}, ensure_ascii=False),
                    image_url=img,
                    unit="套",
                    is_default=True,
                    sort_order=1,
                    reference_purchase_price=55,
                    stock=20,
                    status="启用",
                ),
            )
            variants[(name, "整套")] = parent
            for idx, child in enumerate(["大号", "中号", "小号"], start=2):
                variants[(name, child)] = add(
                    db,
                    ProductVariant(
                        product_id=product.id,
                        code=f"{code}-{idx}",
                        specification=child,
                        specification_values=json.dumps({"型号": child}, ensure_ascii=False),
                        image_url=img,
                        unit="个",
                        is_default=False,
                        sort_order=idx,
                        reference_purchase_price=18 if child == "中号" else 0,
                        stock=20,
                        status="启用",
                    ),
                )
        else:
            variant = add(
                db,
                ProductVariant(
                    product_id=product.id,
                    code=f"{code}-1",
                    specification=spec,
                    specification_values=json.dumps({"高度" if "高" in spec else "盆径": spec}, ensure_ascii=False),
                    image_url=img,
                    unit=unit,
                    is_default=True,
                    sort_order=1,
                    reference_purchase_price=purchase,
                    sale_price=sale,
                    monthly_rental_price=rent,
                    stock=stock,
                    status="启用",
                ),
            )
            variants[(name, spec)] = variant
        products[name] = product
    return products, variants


def seed_customers_projects(db, employees):
    areas = [
        ("A区", employees["任飞扬"]),
        ("B区", employees["任飞扬"]),
        ("C区", employees["伍龙辉"]),
        ("番禺区", employees["任飞扬"]),
        ("天河区", employees["伍龙辉"]),
    ]
    for area, supervisor in areas:
        add(db, CustomerAreaSetting(area=area, supervisor_name=supervisor.name, supervisor_phone=supervisor.phone, status="启用"))

    customer_data = [
        ("企业客户", "广州市场建设管理服务中心", "市场建设绿植租摆项目", "A区", "任飞扬", "13922233362", "周海强", "13711160028", "广东省广州市海珠区昌岗街新凤凰创意园34栋3楼"),
        ("企业客户", "广东岭南科创园", "岭南科创园室外养护项目", "B区", "任飞扬", "13922233362", "周海强", "13711160028", "广州市番禺区兴业大道88号"),
        ("项目客户", "南沙港航办公楼", "南沙港航办公楼租摆项目", "C区", "伍龙辉", "17688855443", "周海强", "13711160028", "广州市南沙区港前大道10号"),
        ("企业客户", "越秀金融中心", "越秀金融中心临时销售项目", "天河区", "伍龙辉", "17688855443", "周海强", "13711160028", "广州市天河区珠江新城华夏路8号"),
        ("个人客户", "陈小姐", "", "番禺区", "任飞扬", "13922233362", "", "", "广州市番禺区大学城外环西路"),
    ]
    customers, projects = [], []
    for idx, item in enumerate(customer_data, start=1):
        ctype, name, project_name, area, sup_name, sup_phone, maint_name, maint_phone, address = item
        customer = add(
            db,
            Customer(
                name=name,
                customer_type=ctype,
                project_name=project_name,
                area=area,
                supervisor_name=sup_name,
                supervisor_phone=sup_phone,
                contact_person=["李主任", "黄经理", "林主管", "王小姐", "陈小姐"][idx - 1],
                phone=["13822220001", "13822220002", "13822220003", "13822220004", "13822220005"][idx - 1],
                maintainer_name=maint_name,
                maintainer_phone=maint_phone,
                address=address,
                status="启用",
            ),
        )
        customers.append(customer)
        project = add(
            db,
            Project(
                code=f"PRJ-{idx:05d}",
                customer_id=customer.id,
                name=project_name or f"{name}个人绿植服务",
                address=address,
                business_types=["租摆,室外养护", "室外养护", "租摆", "销售", "销售"][idx - 1],
                plant_source=["新采购", "原有盘点", "新采购", "客户自提", "新采购"][idx - 1],
                supervisor_id=employees[sup_name].id,
                customer_service_id=employees["梁小敏"].id,
                start_date=date(2026, 8, idx),
                status="进行中",
                notes="真实样例数据，可直接用于测试订单、采购、仓库、配送和费用流程。",
            ),
        )
        projects.append(project)
        add(db, ProjectContact(project_id=project.id, name=customer.contact_person, phone=customer.phone, position="项目负责人", contact_type="负责人", priority=1))
        if maint_name:
            add(db, ProjectContact(project_id=project.id, name=maint_name, phone=maint_phone, position="养护员", contact_type="养护员", priority=0))
        add(db, ProjectMaintainer(project_id=project.id, employee_id=employees["周海强"].id, area_description="项目全部绿植区域", is_primary=True, start_date=project.start_date, status="负责中"))
        floor = add(db, ProjectLocation(project_id=project.id, name=f"{idx + 5}楼", location_type="楼层", sort_order=1))
        add(db, ProjectLocation(project_id=project.id, parent_id=floor.id, name=["总经理办公室", "园区主入口", "前台大厅", "会议室", "客厅阳台"][idx - 1], location_type="区域", sort_order=1))
    return customers, projects


def seed_project_plants(db, projects, products, variants, employees):
    plants = []
    for idx, project in enumerate(projects, start=1):
        location = db.scalar(select(ProjectLocation).where(ProjectLocation.project_id == project.id, ProjectLocation.location_type == "区域"))
        product_name, spec, qty = [
            ("天堂鸟", "高1.8m", 2),
            ("杀虫药", "500ml", 5),
            ("单杆发财树", "高1.6m", 3),
            ("小绿萝", "180#", 12),
            ("小绿萝", "180#", 6),
        ][idx - 1]
        plant = add(
            db,
            ProjectPlant(
                project_id=project.id,
                location_id=location.id,
                product_id=products[product_name].id,
                specification=spec,
                quantity=qty,
                unit=variants[(product_name, spec)].unit,
                decorative_pot="福字盆中号" if product_name != "杀虫药" else "",
                source="新采购" if idx != 2 else "养护耗材",
                maintainer_id=employees["周海强"].id,
                entry_date=TODAY - timedelta(days=idx + 3),
                billing_start_date=TODAY - timedelta(days=idx),
                status="在场",
                notes="真实样例：按项目位置记录植物/耗材。",
            ),
        )
        plants.append(plant)
        add(db, ProjectPlantChange(project_id=project.id, plant_id=plant.id, location_id=location.id, product_id=plant.product_id, change_type="进场录入", source_type="初始化", source_no=f"INIT-{idx:03d}", quantity_before=0, quantity_after=qty, quantity_delta=qty, unit=plant.unit, operator="梁小敏", notes="初始化项目植物清单"))
    return plants


def seed_contract_finance(db, projects, employees):
    contracts = []
    for idx, project in enumerate(projects, start=1):
        amount = [9750, 6800, 5200, 1850, 680][idx - 1]
        contract = add(
            db,
            Contract(
                project_id=project.id,
                contract_no=f"HT2026{idx:04d}",
                name=f"{project.name}服务合同",
                contract_type="整体合同" if idx < 4 else "分体合同",
                business_types=project.business_types,
                effective_date=project.start_date or TODAY,
                end_date=date(2027, 7, 31),
                billing_start_date=project.start_date or TODAY,
                billing_cycle="月付",
                amount=amount,
                reminder_days=30,
                status="生效",
                notes="真实样例合同，用于应收、开票、收款测试。",
            ),
        )
        contracts.append(contract)
        receivable = add(db, ReceivableRecord(project_id=project.id, contract_id=contract.id, receivable_no=f"YS202608{idx:04d}", billing_period="2026-08", due_date=TODAY + timedelta(days=idx), amount=amount, invoice_amount=amount if idx <= 3 else 0, received_amount=amount if idx <= 2 else 0, receivable_type="合同应收", status="已收款" if idx <= 2 else ("已开票" if idx == 3 else "待收款"), notes="8月服务费"))
        invoice = add(db, InvoiceRecord(invoice_no=f"FP202608{idx:04d}", project_id=project.id, contract_id=contract.id, invoice_date=TODAY - timedelta(days=idx), billing_period="2026-08", amount=amount, tax_amount=round(amount * 0.03, 2), invoice_type="普通发票", payer_name=project.name, handler=employees["伍龙辉"].name, source_no=receivable.receivable_no, status="已开票" if idx <= 3 else "待开票", notes="真实样例发票"))
        if idx <= 2:
            add(db, ReceiptRecord(receipt_no=f"SK202608{idx:04d}", project_id=project.id, contract_id=contract.id, invoice_id=invoice.id, receipt_date=TODAY, billing_period="2026-08", amount=amount, payment_method="银行转账", payer_name=project.name, handler=employees["伍龙辉"].name, source_no=invoice.invoice_no, status="已收款", notes="真实样例收款"))
    return contracts


def seed_orders_purchase_inventory(db, projects, products, variants, employees):
    order_specs = [
        ("ZB000001", "租赁订单", projects[0], "天堂鸟", "高1.8m", 2, 30, True, True, "待采购"),
        ("XS000001", "销售订单", projects[3], "小绿萝", "180#", 20, 8, True, True, "待处理"),
        ("HH000001", "换花订单", projects[0], "单杆发财树", "高1.6m", 1, 35, True, True, "待审批"),
        ("YH000001", "养护订单", projects[1], "杀虫药", "500ml", 3, 28, True, False, "待采购"),
        ("CH000001", "撤花订单", projects[2], "单杆发财树", "高1.6m", 1, 0, False, True, "待配送"),
    ]
    orders = []
    for idx, (no, otype, project, product_name, spec, qty, price, need_purchase, need_delivery, status) in enumerate(order_specs, start=1):
        order = add(db, BusinessOrder(order_no=no, order_type=otype, project_id=project.id, project_name=project.name, customer_name=db.get(Customer, project.customer_id).name, requester=employees["梁小敏"].name if idx != 3 else employees["周海强"].name, contact_phone=employees["梁小敏"].phone, order_date=TODAY - timedelta(days=idx), expected_date=TODAY + timedelta(days=idx), priority="普通" if idx != 3 else "加急", need_purchase=need_purchase, need_delivery=need_delivery, status=status, notes="真实样例订单，可用于后续生成采购、出库、安排。"))
        variant = variants[(product_name, spec)]
        add(db, BusinessOrderItem(order_id=order.id, product_id=products[product_name].id, variant_id=variant.id, product_name=product_name, variant_name=spec, location_text=["8楼总经理办公室", "客户自提", "前台大厅", "室外园区", "6楼会议室"][idx - 1], quantity=qty, unit=variant.unit, unit_price=price, amount=qty * price))
        orders.append(order)

    for idx, order in enumerate(orders, start=1):
        item = db.scalar(select(BusinessOrderItem).where(BusinessOrderItem.order_id == order.id))
        purchase = add(db, PurchaseOrder(order_no=f"CG202608{idx:04d}", supplier=["芳村花卉基地", "岭南花场", "番禺绿植基地", "农资批发部", "福字盆厂家"][idx - 1], purchaser=employees["赵俊杰"].name, purchase_date=TODAY - timedelta(days=max(0, 5 - idx)), delivery_method=["入库", "入库", "货拉拉", "快递", "入库"][idx - 1], freight_fee=[80, 50, 0, 12, 60][idx - 1], hll_fee=[0, 0, 90, 0, 0][idx - 1], status=["已入库", "待入库", "待采购", "已入库", "待采购"][idx - 1], notes=f"关联订单 {order.order_no}"))
        received = item.quantity if purchase.status == "已入库" else 0
        add(db, PurchaseOrderItem(order_id=purchase.id, product_id=item.product_id, variant_id=item.variant_id, product_name=item.product_name, variant_name=item.variant_name, quantity=item.quantity, received_quantity=received, unit=item.unit, unit_price=max(item.unit_price * 0.55, 1), notes="真实样例采购明细"))
        if received:
            add(db, InventoryMovement(product_id=item.product_id, variant_id=item.variant_id, product_name=item.product_name, variant_name=item.variant_name, movement_type="采购入库", direction="入库", quantity=received, before_stock=0, after_stock=received, unit=item.unit, unit_price=max(item.unit_price * 0.55, 1), total_amount=received * max(item.unit_price * 0.55, 1), source_type="采购单", source_no=purchase.order_no, operator=employees["赵俊杰"].name, notes="真实采购入库"))
        if idx <= 5:
            outbound = add(db, OutboundOrder(order_no=f"CK202608{idx:04d}", outbound_type=order.order_type.replace("订单", "出库"), project_name=order.project_name, handler=employees["梁小敏"].name, outbound_date=TODAY + timedelta(days=idx), status="待出库" if idx >= 3 else "已出库", notes=f"关联订单 {order.order_no}"))
            add(db, OutboundOrderItem(order_id=outbound.id, product_id=item.product_id, variant_id=item.variant_id, product_name=item.product_name, variant_name=item.variant_name, quantity=item.quantity, unit=item.unit, unit_price=item.unit_price, notes="真实样例出库明细"))
    return orders


def seed_schedule_workflow_misc(db, projects, orders, employees):
    vehicle_data = [
        ("粤A7L58F", "小货车", "周海强"),
        ("粤A3Q91K", "面包车", "周海强"),
        ("粤A8P26D", "货拉拉外协", ""),
        ("粤A5M63H", "电动三轮", "周海强"),
        ("粤A2S77N", "备用车", ""),
    ]
    vehicles = []
    for idx, (plate, vtype, driver) in enumerate(vehicle_data, start=1):
        vehicles.append(add(db, Vehicle(plate_no=plate, vehicle_type=vtype, driver_name=driver, status="可用" if idx != 5 else "保养中", insurance_expiry=TODAY + timedelta(days=80 + idx), inspection_expiry=TODAY + timedelta(days=140 + idx), maintenance_due_date=TODAY + timedelta(days=25 + idx), reminder_days=30, reminder_to="伍龙辉,任飞扬", notes="真实样例车辆")))

    for idx, order in enumerate(orders, start=1):
        add(db, ScheduleTask(task_no=f"AP202608{idx:04d}", schedule_date=TODAY + timedelta(days=idx), task_type="配送" if order.need_delivery else "养护", source_type="订单", source_no=order.order_no, project_name=order.project_name, address=projects[idx - 1].address, driver_id=employees["周海强"].id, assistant_ids=str(employees["赵俊杰"].id) if idx % 2 == 0 else "", vehicle_id=vehicles[(idx - 1) % len(vehicles)].id, planned_start=f"{8 + idx}:00", planned_end=f"{10 + idx}:30", item_summary=db.scalar(select(BusinessOrderItem.product_name).where(BusinessOrderItem.order_id == order.id)) or "", status="待发布" if idx <= 2 else "已发布", notes="真实样例排班"))

    for idx, project in enumerate(projects, start=1):
        add(db, ApprovalRule(project_id=project.id, purchase_requires_approval=idx in [1, 3], exchange_annual_limit=[300, 500, 400, 200, 100][idx - 1], approver_role="经理" if idx in [1, 3] else "主管", approver_name="伍龙辉" if idx in [1, 3] else "任飞扬", status="启用", notes="真实样例审批规则"))

    for idx, order in enumerate(orders, start=1):
        add(db, ApprovalRequest(request_no=f"SP202608{idx:04d}", approval_type="采购审批" if idx % 2 == 0 else "换花审批", source_type="订单", source_id=order.id, source_no=order.order_no, project_id=order.project_id, project_name=order.project_name, applicant=order.requester, amount=180 + idx * 45, reason="按项目审批规则触发", approver_role="经理", approver_name="伍龙辉", status="待审批" if idx <= 3 else "已通过", decision_comment="" if idx <= 3 else "同意执行", decided_by="" if idx <= 3 else "伍龙辉", decided_at=None if idx <= 3 else datetime.now(UTC)))

    for idx, project in enumerate(projects, start=1):
        plan = add(db, MaintenancePlan(plan_no=f"YHPA202608{idx:04d}", project_id=project.id, project_name=project.name, maintainer_id=employees["周海强"].id, area_description="项目全部养护区域", frequency_type="每月次数", frequency_value="4次/月" if idx <= 3 else "按需", service_content="浇水、修剪、清洁叶面、病虫害检查", start_date=TODAY - timedelta(days=10), end_date=TODAY + timedelta(days=330), next_due_date=TODAY + timedelta(days=idx), reminder_days=2, status="启用", notes="真实样例养护计划"))
        add(db, MaintenanceRecord(record_no=f"YHJL202608{idx:04d}", plan_id=plan.id, project_id=project.id, project_name=project.name, maintainer_id=employees["周海强"].id, service_date=TODAY - timedelta(days=idx), area_description=plan.area_description, work_content="完成常规浇水、黄叶清理和盆面整理", site_issue="个别植物叶尖发黄" if idx == 1 else "", handle_result="已修剪并提醒下次观察" if idx == 1 else "现场状态正常", customer_feedback="客户确认无异常", next_plan_date=TODAY + timedelta(days=idx), status="已完成", notes="真实样例养护记录"))
        add(db, ProjectSalary(project_id=project.id, employee_id=employees["周海强"].id, salary_month="2026-08", amount=[1200, 980, 760, 360, 180][idx - 1], adjustment_reason="项目固定养护工资", status="未结算"))
        add(db, ProjectExpense(project_id=project.id, expense_date=TODAY - timedelta(days=idx), expense_type=["物流费", "农药费", "临工费", "工具费", "花盆更换"][idx - 1], amount=[90, 126, 280, 65, 55][idx - 1], handler="梁小敏", source_no=f"FY202608{idx:04d}", description="真实样例项目费用", status="已确认"))
        add(db, Attachment(target_type="项目", target_id=project.id, target_name=project.name, file_name=f"{project.name}合同摘要.pdf", file_type="application/pdf", file_size=128000 + idx, data_url="data:text/plain;charset=utf-8," + quote("真实样例附件"), notes="真实样例附件", uploader_name="梁小敏"))
        add(db, OperationLog(username="admin", display_name="系统管理员", module="数据初始化", action="创建", target_type="项目", target_id=project.id, target_name=project.name, detail="初始化真实样例数据"))


def main():
    backup = backup_database()
    Base.metadata.create_all(engine)
    upgrade_legacy_sqlite(engine)
    with SessionLocal() as db:
        ensure_legacy_columns(db)
        ensure_admin(db)
        clear_business_data(db)
        ensure_admin(db)
        employees = seed_users_employees(db)
        products, variants = seed_products(db)
        customers, projects = seed_customers_projects(db, employees)
        seed_project_plants(db, projects, products, variants, employees)
        seed_contract_finance(db, projects, employees)
        orders = seed_orders_purchase_inventory(db, projects, products, variants, employees)
        seed_schedule_workflow_misc(db, projects, orders, employees)
        db.commit()
    print(f"真实样例数据已重建完成。备份：{backup or '无旧数据库'}")


if __name__ == "__main__":
    main()
