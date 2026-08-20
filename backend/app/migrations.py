from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


SQLITE_TABLES = {
    "customer_area_settings": """
        CREATE TABLE IF NOT EXISTS customer_area_settings (
            id INTEGER NOT NULL PRIMARY KEY,
            area VARCHAR(64) NOT NULL UNIQUE,
            supervisor_name VARCHAR(64) NOT NULL DEFAULT '',
            supervisor_phone VARCHAR(32) NOT NULL DEFAULT '',
            status VARCHAR(16) NOT NULL DEFAULT '启用',
            created_at DATETIME
        )
    """,
    "product_categories": """
        CREATE TABLE IF NOT EXISTS product_categories (
            id INTEGER NOT NULL PRIMARY KEY,
            name VARCHAR(64) NOT NULL UNIQUE,
            sort_order INTEGER NOT NULL DEFAULT 100,
            status VARCHAR(16) NOT NULL DEFAULT '启用',
            created_at DATETIME
        )
    """,
}


SQLITE_COLUMNS = {
    "customers": {
        "customer_type": "VARCHAR(64) NOT NULL DEFAULT '普通客户'",
        "project_name": "VARCHAR(128) NOT NULL DEFAULT ''",
        "area": "VARCHAR(64) NOT NULL DEFAULT ''",
        "supervisor_name": "VARCHAR(64) NOT NULL DEFAULT ''",
        "supervisor_phone": "VARCHAR(32) NOT NULL DEFAULT ''",
        "maintainer_name": "VARCHAR(64) NOT NULL DEFAULT ''",
        "maintainer_phone": "VARCHAR(32) NOT NULL DEFAULT ''",
    },
    "products": {
        "image_url": "VARCHAR(500) NOT NULL DEFAULT ''",
        "image_urls": "TEXT NOT NULL DEFAULT ''",
        "specification_items": "TEXT NOT NULL DEFAULT ''",
        "purchase_unit": "VARCHAR(32) NOT NULL DEFAULT '件'",
        "base_unit": "VARCHAR(32) NOT NULL DEFAULT '件'",
        "project_unit": "VARCHAR(32) NOT NULL DEFAULT '件'",
        "conversion_rate": "FLOAT NOT NULL DEFAULT 1",
        "project_conversion_rate": "FLOAT NOT NULL DEFAULT 1",
        "reference_purchase_price": "FLOAT NOT NULL DEFAULT 0",
        "monthly_rental_price": "FLOAT NOT NULL DEFAULT 0",
        "replacement_cost_price": "FLOAT NOT NULL DEFAULT 0",
        "min_sale_price": "FLOAT NOT NULL DEFAULT 0",
        "package_conversion_enabled": "BOOLEAN NOT NULL DEFAULT 0",
        "status": "VARCHAR(16) NOT NULL DEFAULT '启用'",
    },
    "employees": {
        "department": "VARCHAR(64) NOT NULL DEFAULT ''",
        "business_roles": "VARCHAR(255) NOT NULL DEFAULT ''",
        "module_permissions": "TEXT NOT NULL DEFAULT ''",
        "product_category_permissions": "TEXT NOT NULL DEFAULT ''",
        "leave_date": "DATE",
        "login_enabled": "BOOLEAN NOT NULL DEFAULT 0",
        "responsibility": "TEXT NOT NULL DEFAULT ''",
    },
    "users": {
        "module_permissions": "TEXT NOT NULL DEFAULT ''",
        "product_category_permissions": "TEXT NOT NULL DEFAULT ''",
    },
    "product_variants": {
        "specification_values": "TEXT NOT NULL DEFAULT ''",
        "image_url": "TEXT NOT NULL DEFAULT ''",
        "unit": "VARCHAR(32) NOT NULL DEFAULT '盆'",
        "is_default": "BOOLEAN NOT NULL DEFAULT 0",
        "sort_order": "INTEGER NOT NULL DEFAULT 100",
        "conversion_quantity": "FLOAT NOT NULL DEFAULT 1",
        "package_type": "VARCHAR(16) NOT NULL DEFAULT '单品'",
        "bundle_components": "TEXT NOT NULL DEFAULT ''",
        "reference_purchase_price": "FLOAT NOT NULL DEFAULT 0",
        "sale_price": "FLOAT NOT NULL DEFAULT 0",
        "monthly_rental_price": "FLOAT NOT NULL DEFAULT 0",
        "replacement_cost_price": "FLOAT NOT NULL DEFAULT 0",
        "min_sale_price": "FLOAT NOT NULL DEFAULT 0",
        "stock": "FLOAT NOT NULL DEFAULT 0",
        "status": "VARCHAR(16) NOT NULL DEFAULT '启用'",
    },
    "purchase_orders": {
        "supplier": "VARCHAR(128) NOT NULL DEFAULT ''",
        "purchaser": "VARCHAR(64) NOT NULL DEFAULT ''",
        "purchase_date": "DATE",
        "delivery_method": "VARCHAR(32) NOT NULL DEFAULT '入库'",
        "freight_fee": "FLOAT NOT NULL DEFAULT 0",
        "hll_fee": "FLOAT NOT NULL DEFAULT 0",
        "status": "VARCHAR(16) NOT NULL DEFAULT '待采购'",
        "notes": "TEXT NOT NULL DEFAULT ''",
    },
    "purchase_order_items": {
        "variant_id": "INTEGER",
        "variant_name": "VARCHAR(128) NOT NULL DEFAULT ''",
        "received_quantity": "FLOAT NOT NULL DEFAULT 0",
    },
    "inventory_movements": {
        "variant_id": "INTEGER",
        "variant_name": "VARCHAR(128) NOT NULL DEFAULT ''",
        "before_stock": "FLOAT NOT NULL DEFAULT 0",
        "after_stock": "FLOAT NOT NULL DEFAULT 0",
        "unit_price": "FLOAT NOT NULL DEFAULT 0",
        "total_amount": "FLOAT NOT NULL DEFAULT 0",
    },
    "outbound_order_items": {
        "variant_id": "INTEGER",
        "variant_name": "VARCHAR(128) NOT NULL DEFAULT ''",
    },
    "business_order_items": {
        "variant_id": "INTEGER",
        "variant_name": "VARCHAR(128) NOT NULL DEFAULT ''",
        "location_text": "VARCHAR(255) NOT NULL DEFAULT ''",
    },
    "projects": {
        "address": "VARCHAR(255) NOT NULL DEFAULT ''",
        "business_types": "VARCHAR(255) NOT NULL DEFAULT '租摆'",
        "plant_source": "VARCHAR(32) NOT NULL DEFAULT '新采购'",
        "supervisor_id": "INTEGER",
        "customer_service_id": "INTEGER",
        "start_date": "DATE",
        "notes": "TEXT NOT NULL DEFAULT ''",
    },
    "project_plants": {
        "decorative_pot": "VARCHAR(128) NOT NULL DEFAULT ''",
        "maintainer_id": "INTEGER",
        "billing_start_date": "DATE",
    },
    "contracts": {
        "business_types": "VARCHAR(255) NOT NULL DEFAULT '租摆'",
        "billing_start_date": "DATE",
        "reminder_days": "INTEGER NOT NULL DEFAULT 30",
    },
    "maintenance_records": {
        "plan_id": "INTEGER",
        "customer_feedback": "TEXT NOT NULL DEFAULT ''",
        "next_plan_date": "DATE",
        "generated_order_no": "VARCHAR(64) NOT NULL DEFAULT ''",
    },
    "vehicles": {
        "maintenance_due_date": "DATE",
        "reminder_days": "INTEGER NOT NULL DEFAULT 30",
        "reminder_to": "VARCHAR(255) NOT NULL DEFAULT ''",
    },
}


def upgrade_legacy_sqlite(engine: Engine):
    """Add phase-one columns without deleting existing local development data."""
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table_sql in SQLITE_TABLES.values():
            connection.execute(text(table_sql))
        for table, columns in SQLITE_COLUMNS.items():
            if table not in tables:
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}'))
