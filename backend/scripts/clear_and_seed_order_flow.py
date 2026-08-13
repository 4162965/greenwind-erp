from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, SessionLocal, engine
from app.migrations import upgrade_legacy_sqlite
from app.models import (
    ApprovalRequest,
    BusinessOrder,
    BusinessOrderItem,
    InventoryMovement,
    OutboundOrder,
    OutboundOrderItem,
    PurchaseOrder,
    PurchaseOrderItem,
    ScheduleTask,
)
from scripts.seed_order_status_cases import seed as seed_order_status_cases


def backup_database() -> Path | None:
    db_path = BACKEND_DIR / "greenwind.db"
    if not db_path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = db_path.with_name(f"greenwind.before-clear-orders-{stamp}.db")
    shutil.copy2(db_path, target)
    return target


def count_rows(db, tables: list[str]) -> dict[str, int]:
    return {table: int(db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0) for table in tables}


def clear_order_flow_data() -> tuple[Path | None, dict[str, int], dict[str, int]]:
    Base.metadata.create_all(engine)
    upgrade_legacy_sqlite(engine)
    backup = backup_database()
    tables = [
        "approval_requests",
        "schedule_tasks",
        "inventory_movements",
        "outbound_order_items",
        "outbound_orders",
        "purchase_order_items",
        "purchase_orders",
        "business_order_items",
        "business_orders",
    ]
    with SessionLocal() as db:
        before = count_rows(db, tables)
        for model in [
            ApprovalRequest,
            ScheduleTask,
            InventoryMovement,
            OutboundOrderItem,
            OutboundOrder,
            PurchaseOrderItem,
            PurchaseOrder,
            BusinessOrderItem,
            BusinessOrder,
        ]:
            db.execute(delete(model))
        db.commit()
        after = count_rows(db, tables)
    return backup, before, after


def main() -> None:
    backup, before, after = clear_order_flow_data()
    print("已备份数据库：", backup or "未找到 greenwind.db，跳过备份")
    print("清理前：")
    for table, value in before.items():
        print(f"  {table}: {value}")
    print("清理后：")
    for table, value in after.items():
        print(f"  {table}: {value}")
    seed_order_status_cases()
    with SessionLocal() as db:
        seeded = count_rows(
            db,
            [
                "business_orders",
                "business_order_items",
                "purchase_orders",
                "purchase_order_items",
                "outbound_orders",
                "outbound_order_items",
                "schedule_tasks",
                "approval_requests",
            ],
        )
    print("重新生成后：")
    for table, value in seeded.items():
        print(f"  {table}: {value}")


if __name__ == "__main__":
    main()
