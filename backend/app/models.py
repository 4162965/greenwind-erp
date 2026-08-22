from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(64))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="admin")
    module_permissions: Mapped[str] = mapped_column(Text, default="")
    product_category_permissions: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(64), default="", index=True)
    display_name: Mapped[str] = mapped_column(String(64), default="")
    module: Mapped[str] = mapped_column(String(64), default="", index=True)
    action: Mapped[str] = mapped_column(String(64), default="", index=True)
    target_type: Mapped[str] = mapped_column(String(64), default="")
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    target_name: Mapped[str] = mapped_column(String(128), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(64), default="", index=True)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    target_name: Mapped[str] = mapped_column(String(128), default="", index=True)
    file_name: Mapped[str] = mapped_column(String(255), default="")
    file_type: Mapped[str] = mapped_column(String(128), default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    data_url: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    uploader_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    uploader_name: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    category: Mapped[str] = mapped_column(String(64), default="未分类")
    project_categories: Mapped[str] = mapped_column(String(255), default="")
    specification: Mapped[str] = mapped_column(String(128), default="")
    unit: Mapped[str] = mapped_column(String(32), default="件")
    sale_price: Mapped[float] = mapped_column(Float, default=0)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[str] = mapped_column(Text, default="")
    image_urls: Mapped[str] = mapped_column(Text, default="")
    specification_items: Mapped[str] = mapped_column(Text, default="")
    purchase_unit: Mapped[str] = mapped_column(String(32), default="件")
    base_unit: Mapped[str] = mapped_column(String(32), default="件")
    project_unit: Mapped[str] = mapped_column(String(32), default="件")
    conversion_rate: Mapped[float] = mapped_column(Float, default=1)
    project_conversion_rate: Mapped[float] = mapped_column(Float, default=1)
    reference_purchase_price: Mapped[float] = mapped_column(Float, default=0)
    monthly_rental_price: Mapped[float] = mapped_column(Float, default=0)
    replacement_cost_price: Mapped[float] = mapped_column(Float, default=0)
    min_sale_price: Mapped[float] = mapped_column(Float, default=0)
    grid_greenwind_price: Mapped[float] = mapped_column(Float, default=0)
    grid_shengjing_price: Mapped[float] = mapped_column(Float, default=0)
    package_conversion_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(String(16), default="启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    specification: Mapped[str] = mapped_column(String(255), default="")
    specification_values: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str] = mapped_column(Text, default="")
    unit: Mapped[str] = mapped_column(String(32), default="盆")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    conversion_quantity: Mapped[float] = mapped_column(Float, default=1)
    # 兼容旧本地数据库；这两个字段不再暴露给接口和商品界面。
    package_type: Mapped[str] = mapped_column(String(16), default="单品")
    bundle_components: Mapped[str] = mapped_column(Text, default="")
    reference_purchase_price: Mapped[float] = mapped_column(Float, default=0)
    sale_price: Mapped[float] = mapped_column(Float, default=0)
    monthly_rental_price: Mapped[float] = mapped_column(Float, default=0)
    replacement_cost_price: Mapped[float] = mapped_column(Float, default=0)
    min_sale_price: Mapped[float] = mapped_column(Float, default=0)
    grid_greenwind_price: Mapped[float] = mapped_column(Float, default=0)
    grid_shengjing_price: Mapped[float] = mapped_column(Float, default=0)
    stock: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(16), default="启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    supplier: Mapped[str] = mapped_column(String(128), default="")
    purchaser: Mapped[str] = mapped_column(String(64), default="")
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delivery_method: Mapped[str] = mapped_column(String(32), default="入库")
    freight_fee: Mapped[float] = mapped_column(Float, default=0)
    hll_fee: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(16), default="待采购")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"), nullable=True, index=True)
    product_name: Mapped[str] = mapped_column(String(128), default="")
    variant_name: Mapped[str] = mapped_column(String(128), default="")
    quantity: Mapped[float] = mapped_column(Float, default=1)
    received_quantity: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(32), default="件")
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class PurchaseReceipt(Base):
    __tablename__ = "purchase_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_no: Mapped[str] = mapped_column(String(64), index=True)
    supplier: Mapped[str] = mapped_column(String(128), default="")
    purchaser: Mapped[str] = mapped_column(String(64), default="")
    receipt_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_purchase_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    status: Mapped[str] = mapped_column(String(16), default="有未安排")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)


class PurchaseReceiptItem(Base):
    __tablename__ = "purchase_receipt_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("purchase_receipts.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"), nullable=True, index=True)
    product_name: Mapped[str] = mapped_column(String(128), default="")
    variant_name: Mapped[str] = mapped_column(String(128), default="")
    total_quantity: Mapped[float] = mapped_column(Float, default=0)
    available_quantity: Mapped[float] = mapped_column(Float, default=0, index=True)
    unit: Mapped[str] = mapped_column(String(32), default="件")
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)


class PurchaseReceiptAllocation(Base):
    __tablename__ = "purchase_receipt_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_item_id: Mapped[int] = mapped_column(ForeignKey("purchase_receipt_items.id"), index=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("purchase_receipts.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"), nullable=True, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    project_name: Mapped[str] = mapped_column(String(128), default="")
    business_order_id: Mapped[int | None] = mapped_column(ForeignKey("business_orders.id"), nullable=True, index=True)
    business_order_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    quantity: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(32), default="件")
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    total_amount: Mapped[float] = mapped_column(Float, default=0)
    allocation_type: Mapped[str] = mapped_column(String(16), default="项目订单")
    operator: Mapped[str] = mapped_column(String(64), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"), nullable=True, index=True)
    product_name: Mapped[str] = mapped_column(String(128), default="")
    variant_name: Mapped[str] = mapped_column(String(128), default="")
    movement_type: Mapped[str] = mapped_column(String(32), default="盘点调整")
    direction: Mapped[str] = mapped_column(String(8), default="入库")
    quantity: Mapped[float] = mapped_column(Float, default=0)
    before_stock: Mapped[float] = mapped_column(Float, default=0)
    after_stock: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(32), default="件")
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    total_amount: Mapped[float] = mapped_column(Float, default=0)
    source_type: Mapped[str] = mapped_column(String(32), default="")
    source_no: Mapped[str] = mapped_column(String(64), default="")
    operator: Mapped[str] = mapped_column(String(64), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class OutboundOrder(Base):
    __tablename__ = "outbound_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    outbound_type: Mapped[str] = mapped_column(String(32), default="项目领用")
    project_name: Mapped[str] = mapped_column(String(128), default="")
    handler: Mapped[str] = mapped_column(String(64), default="")
    outbound_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="待出库")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class OutboundOrderItem(Base):
    __tablename__ = "outbound_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("outbound_orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"), nullable=True, index=True)
    product_name: Mapped[str] = mapped_column(String(128), default="")
    variant_name: Mapped[str] = mapped_column(String(128), default="")
    quantity: Mapped[float] = mapped_column(Float, default=1)
    unit: Mapped[str] = mapped_column(String(32), default="件")
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class BusinessOrder(Base):
    __tablename__ = "business_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    order_type: Mapped[str] = mapped_column(String(32), default="租赁订单", index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    project_name: Mapped[str] = mapped_column(String(128), default="")
    customer_name: Mapped[str] = mapped_column(String(128), default="")
    requester: Mapped[str] = mapped_column(String(64), default="")
    contact_phone: Mapped[str] = mapped_column(String(32), default="")
    order_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(16), default="普通")
    need_purchase: Mapped[bool] = mapped_column(Boolean, default=False)
    need_delivery: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(16), default="待处理")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class BusinessOrderItem(Base):
    __tablename__ = "business_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("business_orders.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"), nullable=True, index=True)
    product_name: Mapped[str] = mapped_column(String(128), default="")
    variant_name: Mapped[str] = mapped_column(String(128), default="")
    location_text: Mapped[str] = mapped_column(String(255), default="")
    quantity: Mapped[float] = mapped_column(Float, default=1)
    unit: Mapped[str] = mapped_column(String(32), default="件")
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    amount: Mapped[float] = mapped_column(Float, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    customer_type: Mapped[str] = mapped_column(String(64), default="普通客户")
    project_name: Mapped[str] = mapped_column(String(128), default="")
    area: Mapped[str] = mapped_column(String(64), default="")
    supervisor_name: Mapped[str] = mapped_column(String(64), default="")
    supervisor_phone: Mapped[str] = mapped_column(String(32), default="")
    contact_person: Mapped[str] = mapped_column(String(64), default="")
    phone: Mapped[str] = mapped_column(String(32), default="", index=True)
    maintainer_name: Mapped[str] = mapped_column(String(64), default="")
    maintainer_phone: Mapped[str] = mapped_column(String(32), default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(16), default="启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class CustomerAreaSetting(Base):
    __tablename__ = "customer_area_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    area: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    supervisor_name: Mapped[str] = mapped_column(String(64), default="")
    supervisor_phone: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), default="启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    phone: Mapped[str] = mapped_column(String(32), default="", index=True)
    position: Mapped[str] = mapped_column(String(64), default="")
    role: Mapped[str] = mapped_column(String(64), default="员工")
    department: Mapped[str] = mapped_column(String(64), default="")
    business_roles: Mapped[str] = mapped_column(String(255), default="")
    module_permissions: Mapped[str] = mapped_column(Text, default="")
    product_category_permissions: Mapped[str] = mapped_column(Text, default="")
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    leave_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    login_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    responsibility: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="在职")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    address: Mapped[str] = mapped_column(String(255), default="")
    business_types: Mapped[str] = mapped_column(String(255), default="租摆")
    plant_source: Mapped[str] = mapped_column(String(32), default="新采购")
    supervisor_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    customer_service_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="进行中")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ProjectContact(Base):
    __tablename__ = "project_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    phone: Mapped[str] = mapped_column(String(32), default="")
    position: Mapped[str] = mapped_column(String(64), default="")
    contact_type: Mapped[str] = mapped_column(String(32), default="项目负责人")
    priority: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str] = mapped_column(String(255), default="")


class ProjectLocation(Base):
    __tablename__ = "project_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("project_locations.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(128))
    location_type: Mapped[str] = mapped_column(String(32), default="区域")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ProjectMaintainer(Base):
    __tablename__ = "project_maintainers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    area_description: Mapped[str] = mapped_column(String(255), default="全部区域")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="负责中")


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    contract_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    contract_type: Mapped[str] = mapped_column(String(32), default="整体合同")
    business_types: Mapped[str] = mapped_column(String(255), default="租摆")
    effective_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    billing_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_cycle: Mapped[str] = mapped_column(String(32), default="月付")
    amount: Mapped[float] = mapped_column(Float, default=0)
    reminder_days: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(16), default="生效")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ProjectPlant(Base):
    __tablename__ = "project_plants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("project_locations.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    specification: Mapped[str] = mapped_column(String(128), default="")
    quantity: Mapped[float] = mapped_column(Float, default=1)
    unit: Mapped[str] = mapped_column(String(32), default="盆")
    decorative_pot: Mapped[str] = mapped_column(String(128), default="")
    source: Mapped[str] = mapped_column(String(32), default="新采购")
    maintainer_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="在场")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ProjectPlantChange(Base):
    __tablename__ = "project_plant_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("project_plants.id"), nullable=True, index=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("project_locations.id"), nullable=True, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    change_type: Mapped[str] = mapped_column(String(32), default="手工调整")
    source_type: Mapped[str] = mapped_column(String(32), default="")
    source_no: Mapped[str] = mapped_column(String(64), default="")
    quantity_before: Mapped[float] = mapped_column(Float, default=0)
    quantity_after: Mapped[float] = mapped_column(Float, default=0)
    quantity_delta: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(32), default="")
    pot_before: Mapped[str] = mapped_column(String(128), default="")
    pot_after: Mapped[str] = mapped_column(String(128), default="")
    operator: Mapped[str] = mapped_column(String(64), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ProjectSalary(Base):
    __tablename__ = "project_salaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    salary_month: Mapped[str] = mapped_column(String(7), index=True)
    amount: Mapped[float] = mapped_column(Float, default=0)
    adjustment_reason: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(16), default="未结算")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ProjectExpense(Base):
    __tablename__ = "project_expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    expense_date: Mapped[date] = mapped_column(Date, index=True)
    expense_type: Mapped[str] = mapped_column(String(32), default="其他费用", index=True)
    amount: Mapped[float] = mapped_column(Float, default=0)
    handler: Mapped[str] = mapped_column(String(64), default="")
    source_no: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(16), default="已确认")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class MaintenancePlan(Base):
    __tablename__ = "maintenance_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    project_name: Mapped[str] = mapped_column(String(128), default="")
    maintainer_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    area_description: Mapped[str] = mapped_column(String(255), default="全部区域")
    frequency_type: Mapped[str] = mapped_column(String(32), default="每月次数")
    frequency_value: Mapped[str] = mapped_column(String(128), default="")
    service_content: Mapped[str] = mapped_column(Text, default="")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    reminder_days: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(String(16), default="启用")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("maintenance_plans.id"), nullable=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    project_name: Mapped[str] = mapped_column(String(128), default="")
    maintainer_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    service_date: Mapped[date] = mapped_column(Date, index=True)
    area_description: Mapped[str] = mapped_column(String(255), default="")
    work_content: Mapped[str] = mapped_column(Text, default="")
    site_issue: Mapped[str] = mapped_column(Text, default="")
    handle_result: Mapped[str] = mapped_column(Text, default="")
    photos: Mapped[str] = mapped_column(Text, default="")
    customer_feedback: Mapped[str] = mapped_column(Text, default="")
    next_plan_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    generated_order_no: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="已完成")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class InvoiceRecord(Base):
    __tablename__ = "invoice_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("contracts.id"), nullable=True, index=True)
    invoice_date: Mapped[date] = mapped_column(Date, index=True)
    billing_period: Mapped[str] = mapped_column(String(32), default="")
    amount: Mapped[float] = mapped_column(Float, default=0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0)
    invoice_type: Mapped[str] = mapped_column(String(32), default="普通发票")
    payer_name: Mapped[str] = mapped_column(String(128), default="")
    handler: Mapped[str] = mapped_column(String(64), default="")
    source_no: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="已开票")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ReceiptRecord(Base):
    __tablename__ = "receipt_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("contracts.id"), nullable=True, index=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoice_records.id"), nullable=True, index=True)
    receipt_date: Mapped[date] = mapped_column(Date, index=True)
    billing_period: Mapped[str] = mapped_column(String(32), default="")
    amount: Mapped[float] = mapped_column(Float, default=0)
    payment_method: Mapped[str] = mapped_column(String(32), default="银行转账")
    payer_name: Mapped[str] = mapped_column(String(128), default="")
    handler: Mapped[str] = mapped_column(String(64), default="")
    source_no: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="已收款")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ReceivableRecord(Base):
    __tablename__ = "receivable_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receivable_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("contracts.id"), nullable=True, index=True)
    billing_period: Mapped[str] = mapped_column(String(32), default="", index=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[float] = mapped_column(Float, default=0)
    received_amount: Mapped[float] = mapped_column(Float, default=0)
    invoice_amount: Mapped[float] = mapped_column(Float, default=0)
    receivable_type: Mapped[str] = mapped_column(String(32), default="合同应收")
    status: Mapped[str] = mapped_column(String(16), default="待收款", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plate_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(64), default="")
    driver_name: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="可用")
    insurance_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    inspection_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    maintenance_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reminder_days: Mapped[int] = mapped_column(Integer, default=30)
    reminder_to: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ScheduleTask(Base):
    __tablename__ = "schedule_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    schedule_date: Mapped[date] = mapped_column(Date, index=True)
    task_type: Mapped[str] = mapped_column(String(32), default="配送")
    source_type: Mapped[str] = mapped_column(String(32), default="手工")
    source_no: Mapped[str] = mapped_column(String(64), default="")
    project_name: Mapped[str] = mapped_column(String(128), default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    assistant_ids: Mapped[str] = mapped_column(Text, default="")
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True, index=True)
    planned_start: Mapped[str] = mapped_column(String(16), default="")
    planned_end: Mapped[str] = mapped_column(String(16), default="")
    item_summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="待发布")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ApprovalRule(Base):
    __tablename__ = "approval_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True, index=True)
    purchase_requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    exchange_annual_limit: Mapped[float] = mapped_column(Float, default=0)
    approver_role: Mapped[str] = mapped_column(String(64), default="经理")
    approver_name: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="启用")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    approval_type: Mapped[str] = mapped_column(String(32), default="订单审批", index=True)
    source_type: Mapped[str] = mapped_column(String(32), default="订单")
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_no: Mapped[str] = mapped_column(String(64), default="")
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    project_name: Mapped[str] = mapped_column(String(128), default="")
    applicant: Mapped[str] = mapped_column(String(64), default="")
    amount: Mapped[float] = mapped_column(Float, default=0)
    reason: Mapped[str] = mapped_column(Text, default="")
    approver_role: Mapped[str] = mapped_column(String(64), default="经理")
    approver_name: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="待审批", index=True)
    decision_comment: Mapped[str] = mapped_column(Text, default="")
    decided_by: Mapped[str] = mapped_column(String(64), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
