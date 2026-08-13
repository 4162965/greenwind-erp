import json
import time
import urllib.error
import urllib.request
from datetime import date, timedelta


BASE = "http://127.0.0.1:8010/api/v1"


def req(method, path, token=None, data=None):
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(BASE + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            text = response.read().decode("utf-8")
            return response.status, json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} -> {exc.code}: {text}") from exc


def main():
    _, login = req("POST", "/auth/login", data={"username": "admin", "password": "admin123"})
    token = login["access_token"]
    suffix = f"{date.today():%m%d}-{int(time.time()) % 100000}"
    print("login_ok", login.get("user", {}).get("display_name"))

    customer_payload = {
        "customer_type": "企业客户",
        "name": f"流程测试客户{suffix}",
        "project_name": f"流程测试金融中心{suffix}",
        "area": "A区",
        "supervisor_name": "系统管理员",
        "supervisor_phone": "13800000000",
        "contact_person": "测试负责人",
        "phone": "13900000000",
        "maintainer_name": "测试养护员",
        "maintainer_phone": "13700000000",
        "address": "广州市流程测试路88号8楼",
        "status": "启用",
    }
    _, customer = req("POST", "/customers", token, customer_payload)
    print("customer_ok", customer["id"], customer["name"], customer["project_name"])

    _, employees = req("GET", "/employees", token)
    employee_items = employees.get("items", [])
    supervisor = next(
        (employee for employee in employee_items if "主管" in f"{employee.get('position','')},{employee.get('name','')}"),
        None,
    ) or (employee_items[0] if employee_items else None)
    maintainer = next(
        (employee for employee in employee_items if "养护" in f"{employee.get('position','')},{employee.get('name','')}"),
        None,
    ) or supervisor

    project_payload = {
        "code": f"TEST-{suffix}",
        "customer_id": customer["id"],
        "name": customer["project_name"],
        "address": customer["address"],
        "business_types": "租摆,室外养护",
        "plant_source": "新采购",
        "supervisor_id": supervisor["id"] if supervisor else None,
        "customer_service_id": None,
        "start_date": str(date.today()),
        "status": "进行中",
        "notes": "流程测试自动生成",
    }
    _, project = req("POST", "/projects", token, project_payload)
    print("project_ok", project["id"], project["name"], project["customer_name"])

    _, floor = req(
        "POST",
        f"/projects/{project['id']}/locations",
        token,
        {"name": "8楼", "location_type": "楼层", "parent_id": None, "sort_order": 1},
    )
    _, area = req(
        "POST",
        f"/projects/{project['id']}/locations",
        token,
        {"name": "总经理办公室", "location_type": "区域", "parent_id": floor["id"], "sort_order": 1},
    )
    print("location_ok", floor["name"], area["name"])

    if maintainer:
        _, assign = req(
            "POST",
            f"/projects/{project['id']}/maintainers",
            token,
            {
                "employee_id": maintainer["id"],
                "area_description": "8楼总经理办公室",
                "is_primary": True,
                "start_date": str(date.today()),
                "end_date": None,
                "status": "负责中",
            },
        )
        print("maintainer_ok", assign.get("employee_name"))

    contract_payload = {
        "project_id": project["id"],
        "contract_no": f"HT-TEST-{suffix}",
        "name": f"{project['name']}租摆合同",
        "contract_type": "整体合同",
        "business_types": "租摆,室外养护",
        "effective_date": str(date.today()),
        "end_date": str(date.today() + timedelta(days=365)),
        "billing_start_date": str(date.today()),
        "billing_cycle": "月付",
        "amount": 980,
        "reminder_days": 30,
        "status": "生效",
        "notes": "流程测试合同",
    }
    _, contract = req("POST", "/contracts", token, contract_payload)
    print("contract_ok", contract["contract_no"], contract["amount"])

    _, product = req(
        "POST",
        "/products",
        token,
        {
            "code": f"PTEST-{suffix}",
            "name": f"流程测试绿萝{suffix}",
            "category": "植物",
            "specification": "180#",
            "unit": "盆",
            "sale_price": 7,
            "stock": 0,
            "image_url": "",
            "image_urls": "",
            "specification_items": "",
            "purchase_unit": "盆",
            "base_unit": "盆",
            "project_unit": "盆",
            "conversion_rate": 1,
            "project_conversion_rate": 1,
            "reference_purchase_price": 3,
            "monthly_rental_price": 7,
            "replacement_cost_price": 0,
            "min_sale_price": 0,
            "package_conversion_enabled": False,
            "status": "启用",
        },
    )
    print("product_ok", product["id"], product["name"])

    order_payload = {
        "order_no": f"LC-TEST-{suffix}",
        "order_type": "lease",
        "project_id": project["id"],
        "project_name": project["name"],
        "customer_name": customer["name"],
        "requester": customer["maintainer_name"] or customer["contact_person"],
        "contact_phone": customer["maintainer_phone"] or customer["phone"],
        "order_date": str(date.today()),
        "expected_date": str(date.today() + timedelta(days=1)),
        "priority": "普通",
        "need_purchase": False,
        "need_delivery": True,
        "status": "待处理",
        "notes": "流程测试租赁订单",
        "items": [
            {
                "product_id": product["id"],
                "variant_id": None,
                "product_name": product["name"],
                "variant_name": product.get("specification") or "",
                "location_text": "8楼/总经理办公室",
                "quantity": 2,
                "unit": product.get("project_unit") or product.get("unit") or "盆",
                "unit_price": product.get("monthly_rental_price") or product.get("sale_price") or 0,
                "notes": "",
            }
        ],
    }
    _, order = req("POST", "/orders", token, order_payload)
    print("order_ok", order["order_no"], order["project_name"], order["customer_name"], order["items"][0]["product_name"])

    _, done = req("POST", f"/orders/{order['id']}/status", token, {"status": "已完成"})
    print("order_done_ok", done["status"])

    _, plants = req("GET", f"/project-plants?project_id={project['id']}", token)
    plant_items = plants.get("items", [])
    print("plants_ok", plants.get("total"), plant_items[0].get("product_name") if plant_items else "-", plant_items[0].get("location_name") if plant_items else "-")
    print("FLOW_OK")


if __name__ == "__main__":
    main()
