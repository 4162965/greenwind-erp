import os
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_greenwind.db"

from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User
from app.security import hash_password


Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
with SessionLocal() as db:
    db.add(User(username="admin", display_name="测试管理员", password_hash=hash_password("admin123")))
    db.commit()

client = TestClient(app)


def auth_headers():
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def login_headers(username: str, password: str = "admin123"):
    login = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_and_dashboard():
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    dashboard = client.get("/api/v1/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
    assert dashboard.status_code == 200
    assert len(dashboard.json()["metrics"]) == 4


def test_rejects_wrong_password():
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong-password"})
    assert response.status_code == 401


def test_product_crud():
    headers = auth_headers()
    created = client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "code": "SP-001",
            "name": "测试绿植",
            "category": "盆栽",
            "specification": "中号",
            "unit": "盆",
            "sale_price": 88.5,
            "stock": 20,
            "image_url": "data:image/png;base64," + "A" * 800,
            "image_urls": '["data:image/png;base64,dGVzdA=="]',
            "specification_items": '[{"name":"高度","value":"1.8M"},{"name":"冠幅","value":"80cm"}]',
            "purchase_unit": "箱",
            "base_unit": "盆",
            "project_unit": "盆",
            "conversion_rate": 12,
            "project_conversion_rate": 1,
            "package_conversion_enabled": True,
            "status": "启用",
        },
    )
    assert created.status_code == 201
    product_id = created.json()["id"]
    listed = client.get("/api/v1/products?keyword=绿植", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["conversion_rate"] == 12
    assert listed.json()["items"][0]["package_conversion_enabled"] is True
    assert "高度" in listed.json()["items"][0]["specification_items"]
    updated = client.put(f"/api/v1/products/{product_id}", headers=headers, json={"stock": 18})
    assert updated.status_code == 200
    assert updated.json()["stock"] == 18
    variant_180 = client.post(
        f"/api/v1/products/{product_id}/variants",
        headers=headers,
        json={
            "code": "SP-001-180",
            "specification": "规格：180#",
            "specification_values": '{"规格":"180#"}',
            "reference_purchase_price": 20,
            "sale_price": 35,
            "stock": 12,
            "unit": "盆",
            "is_default": True,
            "sort_order": 10,
            "conversion_quantity": 12,
        },
    )
    assert variant_180.status_code == 201
    variant_350 = client.post(
        f"/api/v1/products/{product_id}/variants",
        headers=headers,
        json={"code": "SP-001-350", "specification": "规格：350#", "specification_values": '{"规格":"350#"}'},
    )
    assert variant_350.status_code == 201
    variants = client.get(f"/api/v1/products/{product_id}/variants", headers=headers)
    assert variants.status_code == 200
    assert variants.json()["total"] == 2
    assert variants.json()["items"][0]["is_default"] is True
    assert variants.json()["items"][0]["conversion_quantity"] == 12
    changed = client.put(
        f"/api/v1/products/{product_id}/variants/{variant_180.json()['id']}",
        headers=headers,
        json={"stock": 10},
    )
    assert changed.status_code == 200
    assert changed.json()["stock"] == 10
    deleted = client.delete(f"/api/v1/products/{product_id}", headers=headers)
    assert deleted.status_code == 204


def test_product_and_variant_code_suggestions_and_inventory_variant_code_search():
    headers = auth_headers()
    prefix = f"SP-{date.today().strftime('%Y%m%d')}"
    first = client.get("/api/v1/products/next-code", headers=headers)
    assert first.status_code == 200
    assert first.json()["code"].startswith(prefix)

    product = client.post(
        "/api/v1/products",
        headers=headers,
        json={"code": first.json()["code"], "name": "编码测试绿萝", "category": "植物", "unit": "盆", "purchase_unit": "盆"},
    ).json()
    second = client.get("/api/v1/products/next-code", headers=headers)
    assert second.status_code == 200
    assert second.json()["code"] == f"{prefix}{int(product['code'].replace(prefix, '')) + 1}"

    variant_code = client.get(f"/api/v1/products/{product['id']}/variants/next-code", headers=headers)
    assert variant_code.status_code == 200
    assert variant_code.json()["code"] == f"{product['code']}-1"
    variant = client.post(
        f"/api/v1/products/{product['id']}/variants",
        headers=headers,
        json={"code": variant_code.json()["code"], "specification": "180#", "unit": "盆", "stock": 3},
    ).json()
    next_variant_code = client.get(f"/api/v1/products/{product['id']}/variants/next-code", headers=headers)
    assert next_variant_code.json()["code"] == f"{product['code']}-2"

    inventory = client.get(f"/api/v1/inventory?keyword={variant['code']}", headers=headers)
    assert inventory.status_code == 200
    assert inventory.json()["total"] == 1
    assert inventory.json()["items"][0]["variant_code"] == variant["code"]
    client.delete(f"/api/v1/products/{product['id']}", headers=headers)


def test_purchase_receive_updates_variant_stock_and_price():
    headers = auth_headers()
    product = client.post(
        "/api/v1/products",
        headers=headers,
        json={"code": "PUR-PLANT-001", "name": "采购测试绿萝", "category": "植物", "unit": "盆", "purchase_unit": "盆"},
    ).json()
    variant = client.post(
        f"/api/v1/products/{product['id']}/variants",
        headers=headers,
        json={
            "code": "PUR-PLANT-001-180",
            "specification": "规格：180#",
            "specification_values": '{"规格":"180#"}',
            "unit": "盆",
            "stock": 2,
            "reference_purchase_price": 3,
        },
    ).json()
    order = client.post(
        "/api/v1/purchases",
        headers=headers,
        json={
            "order_no": "CG-TEST-001",
            "supplier": "测试供应商",
            "purchaser": "采购员",
            "purchase_date": "2026-08-08",
            "items": [
                {
                    "product_id": product["id"],
                    "variant_id": variant["id"],
                    "quantity": 5,
                    "unit": "盆",
                    "unit_price": 4.5,
                }
            ],
        },
    )
    assert order.status_code == 201
    early_receive = client.post(f"/api/v1/purchases/{order.json()['id']}/receive", headers=headers)
    assert early_receive.status_code == 400
    purchased = client.post(f"/api/v1/purchases/{order.json()['id']}/mark-purchased", headers=headers)
    assert purchased.status_code == 200
    assert purchased.json()["status"] == "待入库"
    received = client.post(f"/api/v1/purchases/{order.json()['id']}/receive", headers=headers)
    assert received.status_code == 200
    assert received.json()["status"] == "已入库"
    variants = client.get(f"/api/v1/products/{product['id']}/variants", headers=headers).json()["items"]
    assert variants[0]["stock"] == 7
    assert variants[0]["reference_purchase_price"] == 4.5
    movements = client.get("/api/v1/inventory/movements?keyword=CG-TEST-001", headers=headers)
    assert movements.status_code == 200
    assert movements.json()["total"] == 1
    assert movements.json()["items"][0]["movement_type"] == "采购入库"
    assert movements.json()["items"][0]["before_stock"] == 2
    assert movements.json()["items"][0]["after_stock"] == 7
    client.delete(f"/api/v1/products/{product['id']}", headers=headers)


def test_inventory_list_and_adjust_variant_stock():
    headers = auth_headers()
    product = client.post(
        "/api/v1/products",
        headers=headers,
        json={"code": "INV-PLANT-001", "name": "库存测试绿萝", "category": "植物", "unit": "盆", "purchase_unit": "盆"},
    ).json()
    variant = client.post(
        f"/api/v1/products/{product['id']}/variants",
        headers=headers,
        json={
            "code": "INV-PLANT-001-180",
            "specification": "180#",
            "unit": "盆",
            "stock": 2,
            "reference_purchase_price": 3.5,
        },
    ).json()

    listed = client.get("/api/v1/inventory?keyword=库存测试", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["stock"] == 2

    adjusted = client.post(
        "/api/v1/inventory/adjust",
        headers=headers,
        json={"product_id": product["id"], "variant_id": variant["id"], "new_stock": 9},
    )
    assert adjusted.status_code == 200
    variants = client.get(f"/api/v1/products/{product['id']}/variants", headers=headers).json()["items"]
    assert variants[0]["stock"] == 9
    movements = client.get("/api/v1/inventory/movements?movement_type=盘点调整&keyword=库存测试", headers=headers)
    assert movements.status_code == 200
    assert movements.json()["total"] >= 1
    assert movements.json()["items"][0]["before_stock"] == 2
    assert movements.json()["items"][0]["after_stock"] == 9

    rejected = client.post(
        "/api/v1/inventory/adjust",
        headers=headers,
        json={"product_id": product["id"], "variant_id": variant["id"], "new_stock": -1},
    )
    assert rejected.status_code == 400
    client.delete(f"/api/v1/products/{product['id']}", headers=headers)


def test_outbound_order_confirms_and_writes_stock_movement():
    headers = auth_headers()
    product = client.post(
        "/api/v1/products",
        headers=headers,
        json={"code": "OUT-PLANT-001", "name": "出库测试发财树", "category": "植物", "unit": "盆", "purchase_unit": "盆"},
    ).json()
    variant = client.post(
        f"/api/v1/products/{product['id']}/variants",
        headers=headers,
        json={
            "code": "OUT-PLANT-001-M",
            "specification": "中号",
            "unit": "盆",
            "stock": 6,
            "reference_purchase_price": 18,
        },
    ).json()
    created = client.post(
        "/api/v1/inventory/outbound-orders",
        headers=headers,
        json={
            "order_no": "CK-TEST-001",
            "outbound_type": "项目领用",
            "project_name": "金融中心项目",
            "handler": "客服测试",
            "outbound_date": "2026-08-08",
            "items": [{"product_id": product["id"], "variant_id": variant["id"], "quantity": 2, "unit": "盆"}],
        },
    )
    assert created.status_code == 200
    assert created.json()["status"] == "待出库"

    confirmed = client.post(f"/api/v1/inventory/outbound-orders/{created.json()['id']}/confirm", headers=headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "已出库"
    variants = client.get(f"/api/v1/products/{product['id']}/variants", headers=headers).json()["items"]
    assert variants[0]["stock"] == 4
    movements = client.get("/api/v1/inventory/movements?keyword=CK-TEST-001", headers=headers)
    assert movements.status_code == 200
    assert movements.json()["total"] == 1
    assert movements.json()["items"][0]["direction"] == "出库"
    assert movements.json()["items"][0]["before_stock"] == 6
    assert movements.json()["items"][0]["after_stock"] == 4
    client.delete(f"/api/v1/products/{product['id']}", headers=headers)


def test_business_order_create_list_and_status_change():
    headers = auth_headers()
    product = client.post(
        "/api/v1/products",
        headers=headers,
        json={"code": "ORD-PLANT-001", "name": "订单测试绿萝", "category": "植物", "unit": "盆", "sale_price": 12},
    ).json()
    variant = client.post(
        f"/api/v1/products/{product['id']}/variants",
        headers=headers,
        json={"code": "ORD-PLANT-001-180", "specification": "180#", "unit": "盆", "sale_price": 15},
    ).json()
    created = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "order_no": "DD-TEST-001",
            "order_type": "lease",
            "project_name": "金融中心项目",
            "customer_name": "金融中心客户",
            "requester": "客服测试",
            "order_date": "2026-08-08",
            "expected_date": "2026-08-09",
            "need_purchase": True,
            "need_delivery": True,
            "items": [
                {
                    "product_id": product["id"],
                    "variant_id": variant["id"],
                    "location_text": "8楼总经理办公室",
                    "quantity": 3,
                    "unit": "盆",
                }
            ],
        },
    )
    assert created.status_code == 200
    assert created.json()["order_type"] == "租赁订单"
    assert created.json()["items"][0]["unit_price"] == 15
    listed = client.get("/api/v1/orders?order_type=lease&keyword=金融中心", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    changed = client.post(f"/api/v1/orders/{created.json()['id']}/status", headers=headers, json={"status": "已完成"})
    assert changed.status_code == 200
    assert changed.json()["status"] == "已完成"
    client.delete(f"/api/v1/products/{product['id']}", headers=headers)


def test_business_order_generates_purchase_and_outbound_orders():
    headers = auth_headers()
    product = client.post(
        "/api/v1/products",
        headers=headers,
        json={"code": "LINK-PLANT-001", "name": "联动测试幸福树", "category": "植物", "unit": "盆", "purchase_unit": "盆"},
    ).json()
    variant = client.post(
        f"/api/v1/products/{product['id']}/variants",
        headers=headers,
        json={"code": "LINK-PLANT-001-M", "specification": "中号", "unit": "盆", "reference_purchase_price": 22, "stock": 5},
    ).json()
    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "order_no": "DD-LINK-001",
            "order_type": "sales",
            "project_name": "临时销售",
            "customer_name": "测试客户",
            "requester": "客服测试",
            "order_date": "2026-08-08",
            "expected_date": "2026-08-09",
            "items": [{"product_id": product["id"], "variant_id": variant["id"], "quantity": 2, "unit": "盆"}],
        },
    ).json()

    purchase = client.post(f"/api/v1/orders/{order['id']}/create-purchase", headers=headers)
    assert purchase.status_code == 200
    assert purchase.json()["purchase_order_no"] == "CG-DD-LINK-001"
    listed_purchase = client.get("/api/v1/purchases?keyword=CG-DD-LINK-001", headers=headers)
    assert listed_purchase.json()["total"] == 1
    assert listed_purchase.json()["items"][0]["status"] == "待分配"
    assert listed_purchase.json()["items"][0]["items"][0]["unit_price"] == 22
    order_with_purchase = client.get("/api/v1/orders?order_type=sales&keyword=DD-LINK-001", headers=headers).json()["items"][0]
    assert [node["key"] for node in order_with_purchase["progress"]] == ["purchase", "inbound", "outbound", "delivery"]
    assert order_with_purchase["progress"][0]["ref_no"] == "CG-DD-LINK-001"
    assert "description" in order_with_purchase["progress"][0]
    assigned_purchase = client.post(f"/api/v1/purchases/{purchase.json()['purchase_order_id']}/assign", headers=headers, json={"purchaser": "采购员A"})
    assert assigned_purchase.status_code == 200
    assert assigned_purchase.json()["purchaser"] == "采购员A"
    assert assigned_purchase.json()["status"] == "待采购"

    repeated_purchase = client.post(f"/api/v1/orders/{order['id']}/create-purchase", headers=headers)
    assert repeated_purchase.status_code == 200
    assert repeated_purchase.json()["status"] == "exists"

    outbound = client.post(f"/api/v1/orders/{order['id']}/create-outbound", headers=headers)
    assert outbound.status_code == 200
    assert outbound.json()["outbound_order_no"] == "CK-DD-LINK-001"
    listed_outbound = client.get("/api/v1/inventory/outbound-orders?keyword=CK-DD-LINK-001", headers=headers)
    assert listed_outbound.json()["total"] == 1
    assert listed_outbound.json()["items"][0]["items"][0]["unit_price"] == 22
    order_with_outbound = client.get("/api/v1/orders?order_type=sales&keyword=DD-LINK-001", headers=headers).json()["items"][0]
    outbound_progress = {node["key"]: node for node in order_with_outbound["progress"]}
    assert outbound_progress["outbound"]["ref_no"] == "CK-DD-LINK-001"
    assert outbound_progress["delivery"]["status"] == "未生成"
    assert outbound_progress["outbound"]["actor"] == "客服测试"
    schedule = client.post(f"/api/v1/schedules/from-outbound/{listed_outbound.json()['items'][0]['id']}", headers=headers)
    assert schedule.status_code == 200
    assert schedule.json()["status"] == "created"
    changed_schedule = client.post(f"/api/v1/schedules/{schedule.json()['schedule_id']}/status", headers=headers, json={"status": "已完成"})
    assert changed_schedule.status_code == 200
    linked_order = client.get("/api/v1/orders?order_type=sales&keyword=DD-LINK-001", headers=headers).json()["items"][0]
    assert linked_order["status"] == "已完成"
    linked_progress = {node["key"]: node for node in linked_order["progress"]}
    assert linked_progress["delivery"]["status"] == "已完成"
    assert linked_progress["delivery"]["ref_no"] == "RC-CK-DD-LINK-001"
    client.delete(f"/api/v1/products/{product['id']}", headers=headers)


def test_order_project_scope_for_maintainer_and_supervisor():
    headers = auth_headers()
    with SessionLocal() as db:
        db.add_all(
            [
                User(username="13711112222", display_name="权限养护员", role="养护员", password_hash=hash_password("admin123")),
                User(username="13611112222", display_name="权限主管", role="主管", password_hash=hash_password("admin123")),
            ]
        )
        db.commit()

    customer = client.post("/api/v1/customers", headers=headers, json={"name": "权限测试客户"}).json()
    maintainer = client.post(
        "/api/v1/employees",
        headers=headers,
        json={"name": "权限养护员", "phone": "13711112222", "position": "养护员", "role": "养护员", "department": "绿化部", "login_enabled": True},
    ).json()
    supervisor = client.post(
        "/api/v1/employees",
        headers=headers,
        json={"name": "权限主管", "phone": "13611112222", "position": "主管", "role": "主管", "department": "绿化部", "login_enabled": True},
    ).json()
    project_a = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"code": "SCOPE-A", "customer_id": customer["id"], "name": "权限项目A", "supervisor_id": supervisor["id"]},
    ).json()
    project_b = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"code": "SCOPE-B", "customer_id": customer["id"], "name": "权限项目B"},
    ).json()
    assert client.post(
        f"/api/v1/projects/{project_a['id']}/maintainers",
        headers=headers,
        json={"employee_id": maintainer["id"], "area_description": "全部区域", "is_primary": True},
    ).status_code == 201
    product = client.post(
        "/api/v1/products",
        headers=headers,
        json={"code": "SCOPE-PLANT-001", "name": "权限测试植物", "category": "植物", "unit": "盆"},
    ).json()
    client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "order_no": "SCOPE-ORDER-A",
            "order_type": "lease",
            "project_id": project_a["id"],
            "customer_name": "权限测试客户",
            "items": [{"product_id": product["id"], "quantity": 1, "unit": "盆"}],
        },
    )
    client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "order_no": "SCOPE-ORDER-B",
            "order_type": "lease",
            "project_id": project_b["id"],
            "customer_name": "权限测试客户",
            "items": [{"product_id": product["id"], "quantity": 1, "unit": "盆"}],
        },
    )

    maintainer_headers = login_headers("13711112222")
    maintainer_projects = client.get("/api/v1/projects", headers=maintainer_headers).json()["items"]
    assert [project["name"] for project in maintainer_projects] == ["权限项目A"]
    maintainer_orders = client.get("/api/v1/orders?order_type=lease", headers=maintainer_headers).json()["items"]
    assert [order["order_no"] for order in maintainer_orders] == ["SCOPE-ORDER-A"]
    forbidden = client.post(
        "/api/v1/orders",
        headers=maintainer_headers,
        json={
            "order_no": "SCOPE-FORBIDDEN",
            "order_type": "lease",
            "project_id": project_b["id"],
            "items": [{"product_id": product["id"], "quantity": 1, "unit": "盆"}],
        },
    )
    assert forbidden.status_code == 403

    supervisor_headers = login_headers("13611112222")
    supervisor_orders = client.get("/api/v1/orders?order_type=lease", headers=supervisor_headers).json()["items"]
    assert [order["order_no"] for order in supervisor_orders] == ["SCOPE-ORDER-A"]
    client.delete(f"/api/v1/products/{product['id']}", headers=headers)


def test_customer_crud():
    headers = auth_headers()
    created = client.post(
        "/api/v1/customers",
        headers=headers,
        json={"name": "测试客户", "customer_type": "企业客户", "contact_person": "王经理", "phone": "13800000000"},
    )
    assert created.status_code == 201
    customer_id = created.json()["id"]
    assert client.get("/api/v1/customers?keyword=王经理", headers=headers).json()["total"] == 1
    assert client.put(f"/api/v1/customers/{customer_id}", headers=headers, json={"status": "停用"}).json()["status"] == "停用"
    assert client.delete(f"/api/v1/customers/{customer_id}", headers=headers).status_code == 204


def test_employee_crud():
    headers = auth_headers()
    created = client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "name": "测试员工",
            "phone": "13900000000",
            "position": "业务员",
            "role": "销售",
            "hire_date": "2026-08-04",
            "login_enabled": True,
            "login_password": "emp123456",
        },
    )
    assert created.status_code == 201
    employee_id = created.json()["id"]
    assert client.post("/api/v1/auth/login", json={"username": "13900000000", "password": "emp123456"}).status_code == 200
    assert client.get("/api/v1/employees?keyword=业务员", headers=headers).json()["total"] == 1
    assert client.put(f"/api/v1/employees/{employee_id}", headers=headers, json={"status": "离职"}).json()["status"] == "离职"
    assert client.post("/api/v1/auth/login", json={"username": "13900000000", "password": "emp123456"}).status_code == 403
    assert client.delete(f"/api/v1/employees/{employee_id}", headers=headers).status_code == 204


def test_project_foundation_flow():
    headers = auth_headers()
    customer = client.post(
        "/api/v1/customers",
        headers=headers,
        json={"name": "金融中心客户", "customer_type": "企业客户"},
    ).json()
    employee = client.post(
        "/api/v1/employees",
        headers=headers,
        json={"name": "陈养护", "phone": "13700000000", "position": "养护员", "role": "养护员", "department": "绿化部"},
    ).json()
    product = client.post(
        "/api/v1/products",
        headers=headers,
        json={"code": "PLANT-001", "name": "幸福树", "category": "植物", "unit": "盆", "project_unit": "盆"},
    ).json()
    project_response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "code": "PRJ-001",
            "customer_id": customer["id"],
            "name": "金融中心项目",
            "address": "金融大道1号",
            "business_types": "租摆,室外养护",
            "plant_source": "买断上一家",
            "supervisor_id": employee["id"],
        },
    )
    assert project_response.status_code == 201
    project = project_response.json()
    assert project["customer_name"] == "金融中心客户"

    floor = client.post(
        f"/api/v1/projects/{project['id']}/locations",
        headers=headers,
        json={"name": "8楼", "location_type": "楼层"},
    ).json()
    office = client.post(
        f"/api/v1/projects/{project['id']}/locations",
        headers=headers,
        json={"name": "总经理办公室", "location_type": "区域", "parent_id": floor["id"]},
    ).json()
    assert client.get(f"/api/v1/projects/{project['id']}/locations", headers=headers).json()["total"] == 2

    assert client.post(
        f"/api/v1/projects/{project['id']}/contacts",
        headers=headers,
        json={"name": "王经理", "phone": "13600000000", "priority": 1},
    ).status_code == 201
    assert client.post(
        f"/api/v1/projects/{project['id']}/maintainers",
        headers=headers,
        json={"employee_id": employee["id"], "area_description": "A栋8楼", "is_primary": True},
    ).status_code == 201

    contract_response = client.post(
        "/api/v1/contracts",
        headers=headers,
        json={
            "project_id": project["id"],
            "contract_no": "HT-2026-001",
            "name": "金融中心租摆合同",
            "business_types": "租摆",
            "effective_date": "2026-08-01",
            "end_date": "2027-07-31",
            "amount": 120000,
        },
    )
    assert contract_response.status_code == 201
    assert contract_response.json()["billing_start_date"] == "2026-08-01"
    contract_update = client.put(
        f"/api/v1/contracts/{contract_response.json()['id']}",
        headers=headers,
        json={"reminder_days": 45, "billing_cycle": "季付"},
    )
    assert contract_update.status_code == 200
    assert contract_update.json()["reminder_days"] == 45

    plant_response = client.post(
        "/api/v1/project-plants",
        headers=headers,
        json={
            "project_id": project["id"],
            "location_id": office["id"],
            "product_id": product["id"],
            "specification": "1.8M",
            "quantity": 1,
            "unit": "盆",
            "maintainer_id": employee["id"],
        },
    )
    assert plant_response.status_code == 201
    assert plant_response.json()["location_name"] == "总经理办公室"
    assert plant_response.json()["source"] == "买断上一家"

    salary_response = client.post(
        "/api/v1/project-salaries",
        headers=headers,
        json={"project_id": project["id"], "employee_id": employee["id"], "salary_month": "2026-08", "amount": 1800},
    )
    assert salary_response.status_code == 201
    assert salary_response.json()["employee_name"] == "陈养护"
    duplicate = client.post(
        "/api/v1/project-salaries",
        headers=headers,
        json={"project_id": project["id"], "employee_id": employee["id"], "salary_month": "2026-08", "amount": 1800},
    )
    assert duplicate.status_code == 409
    delete_contract = client.delete(f"/api/v1/contracts/{contract_response.json()['id']}", headers=headers)
    assert delete_contract.status_code == 204


def test_project_cost_report_summarizes_income_and_cost_without_double_counting_outbound():
    headers = auth_headers()
    customer = client.post("/api/v1/customers", headers=headers, json={"name": "成本报表客户"}).json()
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"code": "COST-PRJ-001", "customer_id": customer["id"], "name": "成本报表项目"},
    ).json()
    contract = client.post(
        "/api/v1/contracts",
        headers=headers,
        json={
            "project_id": project["id"],
            "contract_no": "COST-HT-001",
            "name": "成本报表8月合同",
            "effective_date": "2026-08-01",
            "end_date": "2026-08-31",
            "billing_start_date": "2026-08-01",
            "amount": 1000,
        },
    )
    assert contract.status_code == 201
    product = client.post(
        "/api/v1/products",
        headers=headers,
        json={"code": "COST-P-001", "name": "成本报表植物", "category": "植物", "unit": "盆", "reference_purchase_price": 20},
    ).json()
    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "order_no": "COST-DD-001",
            "order_type": "sales",
            "project_id": project["id"],
            "order_date": "2026-08-08",
            "expected_date": "2026-08-09",
            "requester": "客服成本",
            "need_purchase": True,
            "need_delivery": True,
            "items": [{"product_id": product["id"], "quantity": 2, "unit": "盆"}],
        },
    ).json()
    purchase = client.post(f"/api/v1/orders/{order['id']}/create-purchase", headers=headers).json()
    updated_purchase = client.put(
        f"/api/v1/purchases/{purchase['purchase_order_id']}",
        headers=headers,
        json={"freight_fee": 15, "hll_fee": 20, "items": [{"product_id": product["id"], "quantity": 2, "unit": "盆", "unit_price": 20}]},
    )
    assert updated_purchase.status_code == 200
    outbound = client.post(f"/api/v1/orders/{order['id']}/create-outbound", headers=headers)
    assert outbound.status_code == 200
    salary = client.post(
        "/api/v1/project-salaries",
        headers=headers,
        json={"project_id": project["id"], "employee_id": 1, "salary_month": "2026-08", "amount": 300},
    )
    if salary.status_code != 201:
        employee = client.post("/api/v1/employees", headers=headers, json={"name": "成本养护员", "phone": "13599990001"}).json()
        salary = client.post(
            "/api/v1/project-salaries",
            headers=headers,
            json={"project_id": project["id"], "employee_id": employee["id"], "salary_month": "2026-08", "amount": 300},
        )
    assert salary.status_code == 201
    expense = client.post(
        "/api/v1/reports/project-expenses",
        headers=headers,
        json={
            "project_id": project["id"],
            "expense_date": "2026-08-20",
            "expense_type": "临工费用",
            "amount": 120,
            "handler": "主管成本",
            "source_no": "LG-001",
            "description": "临工修剪半天",
        },
    )
    assert expense.status_code == 201
    generated_receivables = client.post(
        f"/api/v1/finance/receivables/generate-from-contract/{contract.json()['id']}",
        headers=headers,
    )
    assert generated_receivables.status_code == 200
    assert generated_receivables.json()["created"] == 1
    invoice = client.post(
        "/api/v1/finance/invoices",
        headers=headers,
        json={
            "invoice_no": "FP-COST-001",
            "project_id": project["id"],
            "contract_id": contract.json()["id"],
            "invoice_date": "2026-08-25",
            "billing_period": "2026-08",
            "amount": 800,
            "tax_amount": 48,
            "payer_name": "成本报表客户",
        },
    )
    assert invoice.status_code == 201
    receipt = client.post(
        "/api/v1/finance/receipts",
        headers=headers,
        json={
            "receipt_no": "SK-COST-001",
            "project_id": project["id"],
            "contract_id": contract.json()["id"],
            "invoice_id": invoice.json()["id"],
            "receipt_date": "2026-08-28",
            "billing_period": "2026-08",
            "amount": 500,
            "payer_name": "成本报表客户",
        },
    )
    assert receipt.status_code == 201

    report = client.get(
        f"/api/v1/reports/project-costs?project_id={project['id']}&start_date=2026-08-01&end_date=2026-08-31",
        headers=headers,
    )
    assert report.status_code == 200
    row = report.json()["items"][0]
    assert row["customer_income"] == 1000
    assert row["purchase_cost"] == 40
    assert row["stock_out_cost"] == 0
    assert row["logistics_cost"] == 35
    assert row["salary_cost"] == 300
    assert row["other_cost"] == 120
    assert row["total_cost"] == 495
    assert row["profit"] == 505
    assert row["invoice_amount"] == 800
    assert row["receipt_amount"] == 500
    assert row["unreceived_amount"] == 300
    expenses = client.get(
        f"/api/v1/reports/project-expenses?project_id={project['id']}&start_date=2026-08-01&end_date=2026-08-31",
        headers=headers,
    )
    assert expenses.status_code == 200
    assert expenses.json()["items"][0]["source_no"] == "LG-001"
    finance_summary = client.get(f"/api/v1/finance/summary?project_id={project['id']}", headers=headers)
    assert finance_summary.status_code == 200
    assert finance_summary.json()["unreceived_amount"] == 300
    receivables = client.get(f"/api/v1/finance/receivables?project_id={project['id']}&keyword=2026-08", headers=headers)
    assert receivables.status_code == 200
    assert receivables.json()["items"][0]["amount"] == 1000
    assert receivables.json()["items"][0]["invoice_amount"] == 800
    assert receivables.json()["items"][0]["received_amount"] == 500
    assert receivables.json()["items"][0]["unreceived_amount"] == 500


def test_vehicle_and_schedule_flow():
    headers = auth_headers()
    driver = client.post(
        "/api/v1/employees",
        headers=headers,
        json={"name": "测试司机", "phone": "13500000001", "position": "司机", "role": "司机"},
    ).json()
    assistant = client.post(
        "/api/v1/employees",
        headers=headers,
        json={"name": "测试跟车", "phone": "13500000002", "position": "跟车配送", "role": "跟车配送"},
    ).json()
    vehicle_response = client.post(
        "/api/v1/vehicles",
        headers=headers,
        json={
            "plate_no": "粤BTEST1",
            "vehicle_type": "面包车",
            "driver_name": "测试司机",
            "status": "可用",
            "insurance_expiry": (date.today() + timedelta(days=10)).isoformat(),
            "maintenance_due_date": (date.today() + timedelta(days=60)).isoformat(),
            "reminder_days": 30,
            "reminder_to": "客服、主管",
        },
    )
    assert vehicle_response.status_code == 201
    vehicle = vehicle_response.json()
    assert vehicle["reminder_status"] == "即将到期"
    assert vehicle["reminder_to"] == "客服、主管"

    vehicle_list = client.get("/api/v1/vehicles?keyword=粤BTEST1", headers=headers)
    assert vehicle_list.status_code == 200
    assert vehicle_list.json()["items"][0]["reminder_status"] == "即将到期"

    schedule_response = client.post(
        "/api/v1/schedules",
        headers=headers,
        json={
            "task_no": "RC-TEST-001",
            "schedule_date": "2026-08-10",
            "task_type": "配送",
            "source_type": "订单",
            "source_no": "DD-TEST-001",
            "project_name": "金融中心项目",
            "address": "金融大道1号",
            "driver_id": driver["id"],
            "assistant_ids": str(assistant["id"]),
            "vehicle_id": vehicle["id"],
            "planned_start": "09:00",
            "planned_end": "11:00",
            "item_summary": "幸福树 × 1盆；绿萝 × 10盆",
        },
    )
    assert schedule_response.status_code == 201
    schedule = schedule_response.json()
    assert schedule["driver_name"] == "测试司机"
    assert schedule["assistant_names"] == "测试跟车"
    assert schedule["vehicle_plate_no"] == "粤BTEST1"

    listed = client.get("/api/v1/schedules?schedule_date=2026-08-10&keyword=金融中心", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    changed = client.post(f"/api/v1/schedules/{schedule['id']}/status", headers=headers, json={"status": "已发布"})
    assert changed.status_code == 200
    assert changed.json()["status"] == "已发布"


def test_generate_schedule_from_order_and_outbound():
    headers = auth_headers()
    driver = client.post(
        "/api/v1/employees",
        headers=headers,
        json={"name": "Schedule Driver", "phone": "13500000031", "position": "driver", "role": "driver"},
    ).json()
    assistant = client.post(
        "/api/v1/employees",
        headers=headers,
        json={"name": "Schedule Assistant", "phone": "13500000032", "position": "assistant", "role": "assistant"},
    ).json()
    vehicle = client.post(
        "/api/v1/vehicles",
        headers=headers,
        json={"plate_no": "TEST-SCH-1", "vehicle_type": "van", "driver_name": "Schedule Driver", "status": "available"},
    ).json()
    order_response = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "order_no": "DD-SCHEDULE-001",
            "order_type": "sales",
            "project_name": "临时销售项目",
            "customer_name": "测试客户",
            "requester": "客服A",
            "order_date": "2026-08-10",
            "expected_date": "2026-08-11",
            "items": [{"product_name": "绿萝", "quantity": 10, "unit": "盆", "unit_price": 12, "location_text": "8楼"}],
        },
    )
    assert order_response.status_code == 200
    generated = client.post(f"/api/v1/schedules/from-order/{order_response.json()['id']}", headers=headers)
    assert generated.status_code == 200
    assert generated.json()["status"] == "created"
    client.post(f"/api/v1/schedules/{generated.json()['schedule_id']}/status", headers=headers, json={"status": "配送中"})
    order_progress = client.get("/api/v1/orders?order_type=sales&keyword=DD-SCHEDULE-001", headers=headers).json()["items"][0]
    assert order_progress["status"] == "配送中"
    listed = client.get("/api/v1/schedules?schedule_date=2026-08-11&keyword=临时销售", headers=headers)
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["source_no"] == "DD-SCHEDULE-001"

    product = client.post(
        "/api/v1/products",
        headers=headers,
        json={"code": "SCH-P-001", "name": "排班测试植物", "category": "植物", "unit": "盆", "purchase_unit": "盆", "stock": 20},
    ).json()
    outbound_response = client.post(
        "/api/v1/inventory/outbound-orders",
        headers=headers,
        json={
            "order_no": "CK-SCHEDULE-001",
            "outbound_type": "项目领用",
            "project_name": "金融中心项目",
            "handler": "客服A",
            "outbound_date": "2026-08-12",
            "items": [{"product_id": product["id"], "quantity": 2, "unit": "盆", "unit_price": 30}],
        },
    )
    assert outbound_response.status_code == 200
    outbound_generated = client.post(
        f"/api/v1/schedules/from-outbound/{outbound_response.json()['id']}",
        headers=headers,
        json={
            "schedule_date": "2026-08-13",
            "driver_id": driver["id"],
            "assistant_ids": str(assistant["id"]),
            "vehicle_id": vehicle["id"],
            "planned_start": "09:00",
            "planned_end": "11:00",
        },
    )
    assert outbound_generated.status_code == 200
    assert outbound_generated.json()["status"] == "created"
    schedule_items = client.get("/api/v1/schedules?schedule_date=2026-08-13&keyword=CK-SCHEDULE-001", headers=headers).json()["items"]
    assert schedule_items[0]["driver_name"] == "Schedule Driver"
    assert schedule_items[0]["assistant_names"] == "Schedule Assistant"
    assert schedule_items[0]["vehicle_plate_no"] == "TEST-SCH-1"
    duplicate = client.post(f"/api/v1/schedules/from-outbound/{outbound_response.json()['id']}", headers=headers)
    assert duplicate.json()["status"] == "exists"


def test_my_schedule_only_returns_assigned_published_tasks():
    headers = auth_headers()
    driver = client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "name": "我的任务司机",
            "phone": "13500000011",
            "position": "司机",
            "role": "司机",
            "login_enabled": True,
            "login_password": "driver123",
        },
    ).json()
    assistant = client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "name": "我的任务跟车",
            "phone": "13500000012",
            "position": "跟车配送",
            "role": "跟车配送",
            "login_enabled": True,
            "login_password": "assist123",
        },
    ).json()
    other = client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "name": "其他司机",
            "phone": "13500000013",
            "position": "司机",
            "role": "司机",
            "login_enabled": True,
            "login_password": "other123",
        },
    ).json()
    schedule = client.post(
        "/api/v1/schedules",
        headers=headers,
        json={
            "task_no": "RC-MY-001",
            "schedule_date": "2026-08-13",
            "task_type": "配送",
            "source_type": "手工",
            "project_name": "我的任务项目",
            "driver_id": driver["id"],
            "assistant_ids": str(assistant["id"]),
            "item_summary": "绿萝 × 3盆",
            "status": "待发布",
        },
    ).json()

    driver_headers = login_headers("13500000011", "driver123")
    assistant_headers = login_headers("13500000012", "assist123")
    other_headers = login_headers("13500000013", "other123")
    assert client.get("/api/v1/schedules/my?schedule_date=2026-08-13", headers=driver_headers).json()["total"] == 0

    client.post(f"/api/v1/schedules/{schedule['id']}/status", headers=headers, json={"status": "已发布"})
    driver_tasks = client.get("/api/v1/schedules/my?schedule_date=2026-08-13", headers=driver_headers).json()["items"]
    assistant_tasks = client.get("/api/v1/schedules/my?schedule_date=2026-08-13", headers=assistant_headers).json()["items"]
    other_tasks = client.get("/api/v1/schedules/my?schedule_date=2026-08-13", headers=other_headers).json()["items"]
    assert [task["task_no"] for task in driver_tasks] == ["RC-MY-001"]
    assert [task["task_no"] for task in assistant_tasks] == ["RC-MY-001"]
    assert other_tasks == []
    assert client.post(f"/api/v1/schedules/{schedule['id']}/status", headers=driver_headers, json={"status": "配送中"}).json()["status"] == "配送中"
    assert client.post(f"/api/v1/schedules/{schedule['id']}/status", headers=driver_headers, json={"status": "已送达"}).json()["status"] == "已送达"
    assert client.post(f"/api/v1/schedules/{schedule['id']}/status", headers=driver_headers, json={"status": "已完成"}).json()["status"] == "已完成"
    unfinished = client.get("/api/v1/schedules/my?schedule_date=2026-08-13&include_done=false", headers=driver_headers).json()["items"]
    assert unfinished == []


def test_workflow_rule_triggers_order_approval_and_decision():
    headers = auth_headers()
    customer = client.post("/api/v1/customers", headers=headers, json={"name": "审批测试客户"}).json()
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"code": "PRJ-APPROVAL-001", "customer_id": customer["id"], "name": "审批测试项目", "business_types": "租摆"},
    ).json()
    rule_response = client.post(
        "/api/v1/workflows/rules",
        headers=headers,
        json={
            "project_id": project["id"],
            "purchase_requires_approval": True,
            "exchange_annual_limit": 100,
            "approver_role": "经理",
            "approver_name": "审批经理",
        },
    )
    assert rule_response.status_code == 201
    product = client.post(
        "/api/v1/products",
        headers=headers,
        json={"code": "APPROVAL-P-001", "name": "审批测试绿萝", "category": "植物", "unit": "盆", "purchase_unit": "盆", "stock": 20},
    ).json()

    order_response = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "order_no": "APPROVAL-ORDER-001",
            "order_type": "exchange",
            "project_id": project["id"],
            "requester": "客服A",
            "order_date": "2026-08-15",
            "need_purchase": True,
            "items": [{"product_id": product["id"], "quantity": 10, "unit": "盆", "unit_price": 12}],
        },
    )
    assert order_response.status_code == 200
    assert order_response.json()["status"] == "待审批"
    approval_progress = {node["key"]: node for node in order_response.json()["progress"]}
    assert approval_progress["approval"]["status"] == "待审批"
    assert approval_progress["approval"]["actor"] == "审批经理"
    blocked_purchase = client.post(f"/api/v1/orders/{order_response.json()['id']}/create-purchase", headers=headers)
    assert blocked_purchase.status_code == 400
    assert "审批通过后" in blocked_purchase.json()["detail"]
    blocked_outbound = client.post(f"/api/v1/orders/{order_response.json()['id']}/create-outbound", headers=headers)
    assert blocked_outbound.status_code == 400
    assert "审批通过后" in blocked_outbound.json()["detail"]
    blocked_schedule = client.post(f"/api/v1/schedules/from-order/{order_response.json()['id']}", headers=headers)
    assert blocked_schedule.status_code == 400
    assert "审批通过后" in blocked_schedule.json()["detail"]
    requests = client.get("/api/v1/workflows/requests?status=待审批&keyword=APPROVAL-ORDER-001", headers=headers).json()["items"]
    assert len(requests) == 1
    assert "采购需求必须审批" in requests[0]["reason"]
    decision = client.post(
        f"/api/v1/workflows/requests/{requests[0]['id']}/decision",
        headers=headers,
        json={"status": "已通过", "decision_comment": "同意采购换花"},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "已通过"
    listed = client.get("/api/v1/orders?order_type=exchange&keyword=APPROVAL-ORDER-001", headers=headers).json()["items"]
    assert listed[0]["status"] == "待处理"
    approved_progress = {node["key"]: node for node in listed[0]["progress"]}
    assert approved_progress["approval"]["status"] == "已通过"
    purchase_after_approval = client.post(f"/api/v1/orders/{order_response.json()['id']}/create-purchase", headers=headers)
    assert purchase_after_approval.status_code == 200
    assert purchase_after_approval.json()["status"] == "created"


def test_my_purchase_only_returns_assigned_orders_and_can_mark_purchased():
    headers = auth_headers()
    employee = client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "name": "Buyer A",
            "phone": "13500000021",
            "position": "buyer",
            "role": "buyer",
            "login_enabled": True,
            "login_password": "buyer123",
        },
    ).json()
    assert employee["name"] == "Buyer A"
    product = client.post(
        "/api/v1/products",
        headers=headers,
        json={"code": "MY-PUR-P-001", "name": "My Purchase Product", "category": "plant", "unit": "pcs", "purchase_unit": "pcs"},
    ).json()
    assigned = client.post(
        "/api/v1/purchases",
        headers=headers,
        json={
            "order_no": "MY-PUR-001",
            "supplier": "",
            "purchaser": "",
            "items": [{"product_id": product["id"], "quantity": 3, "unit": "pcs", "unit_price": 0}],
        },
    )
    assert assigned.status_code == 201
    other = client.post(
        "/api/v1/purchases",
        headers=headers,
        json={
            "order_no": "MY-PUR-OTHER",
            "supplier": "Other Supplier",
            "purchaser": "Buyer B",
            "items": [{"product_id": product["id"], "quantity": 1, "unit": "pcs", "unit_price": 9}],
        },
    )
    assert other.status_code == 201
    assert client.post(f"/api/v1/purchases/{assigned.json()['id']}/assign", headers=headers, json={"purchaser": "Buyer A"}).status_code == 200

    buyer_headers = login_headers("13500000021", "buyer123")
    listed = client.get("/api/v1/purchases/my?include_done=false", headers=buyer_headers)
    assert listed.status_code == 200
    assert [order["order_no"] for order in listed.json()["items"]] == ["MY-PUR-001"]

    saved = client.put(
        f"/api/v1/purchases/{assigned.json()['id']}",
        headers=buyer_headers,
        json={
            "supplier": "Buyer Supplier",
            "freight_fee": 12.5,
            "hll_fee": 20,
            "items": [{"product_id": product["id"], "quantity": 3, "unit": "pcs", "unit_price": 8.8}],
        },
    )
    assert saved.status_code == 200
    assert saved.json()["supplier"] == "Buyer Supplier"
    assert saved.json()["items"][0]["unit_price"] == 8.8

    marked = client.post(f"/api/v1/purchases/{assigned.json()['id']}/mark-purchased", headers=buyer_headers)
    assert marked.status_code == 200
    inbound = client.get("/api/v1/purchases/inbound", headers=headers)
    assert inbound.status_code == 200
    assert "MY-PUR-001" in [order["order_no"] for order in inbound.json()["items"]]
    receive = client.post(f"/api/v1/purchases/{assigned.json()['id']}/receive", headers=headers)
    assert receive.status_code == 200
    inbound_after_receive = client.get("/api/v1/purchases/inbound", headers=headers)
    assert "MY-PUR-001" not in [order["order_no"] for order in inbound_after_receive.json()["items"]]
    after_done = client.get("/api/v1/purchases/my?include_done=false", headers=buyer_headers)
    assert [order["order_no"] for order in after_done.json()["items"]] == []
