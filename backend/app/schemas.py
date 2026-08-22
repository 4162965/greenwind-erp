from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class UserInfo(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    module_permissions: list[str] = []
    product_category_permissions: list[str] = []


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class UserAccountCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=64)
    role: str = Field(default="员工", max_length=64)
    module_permissions: str = ""
    product_category_permissions: str = ""
    password: str = Field(default="123456", min_length=6, max_length=128)
    is_active: bool = True


class UserAccountUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=64)
    role: str | None = Field(default=None, max_length=64)
    module_permissions: str | None = None
    product_category_permissions: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    is_active: bool | None = None


class UserAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    display_name: str
    role: str
    module_permissions: str = ""
    product_category_permissions: str = ""
    is_active: bool
    created_at: datetime


class OperationLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None = None
    username: str = ""
    display_name: str = ""
    module: str = ""
    action: str = ""
    target_type: str = ""
    target_id: int | None = None
    target_name: str = ""
    detail: str = ""
    ip_address: str = ""
    created_at: datetime


class AttachmentBase(BaseModel):
    target_type: str = Field(default="", max_length=64)
    target_id: int | None = None
    target_name: str = Field(default="", max_length=128)
    file_name: str = Field(default="", max_length=255)
    file_type: str = Field(default="", max_length=128)
    file_size: int = Field(default=0, ge=0)
    data_url: str = ""
    notes: str = ""


class AttachmentCreate(AttachmentBase):
    pass


class AttachmentRead(AttachmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uploader_id: int | None = None
    uploader_name: str = ""
    created_at: datetime


class ProductBase(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    category: str = Field(default="未分类", max_length=64)
    specification: str = Field(default="", max_length=128)
    unit: str = Field(default="件", max_length=32)
    sale_price: float = Field(default=0, ge=0)
    stock: int = Field(default=0, ge=0)
    image_url: str = ""
    image_urls: str = ""
    specification_items: str = ""
    purchase_unit: str = Field(default="件", max_length=32)
    base_unit: str = Field(default="件", max_length=32)
    project_unit: str = Field(default="件", max_length=32)
    conversion_rate: float = Field(default=1, gt=0)
    project_conversion_rate: float = Field(default=1, gt=0)
    reference_purchase_price: float = Field(default=0, ge=0)
    monthly_rental_price: float = Field(default=0, ge=0)
    replacement_cost_price: float = Field(default=0, ge=0)
    min_sale_price: float = Field(default=0, ge=0)
    grid_greenwind_price: float = Field(default=0, ge=0)
    grid_shengjing_price: float = Field(default=0, ge=0)
    package_conversion_enabled: bool = False
    status: str = Field(default="启用", max_length=16)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    category: str | None = Field(default=None, max_length=64)
    specification: str | None = Field(default=None, max_length=128)
    unit: str | None = Field(default=None, max_length=32)
    sale_price: float | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    image_url: str | None = None
    image_urls: str | None = None
    specification_items: str | None = None
    purchase_unit: str | None = Field(default=None, max_length=32)
    base_unit: str | None = Field(default=None, max_length=32)
    project_unit: str | None = Field(default=None, max_length=32)
    conversion_rate: float | None = Field(default=None, gt=0)
    project_conversion_rate: float | None = Field(default=None, gt=0)
    reference_purchase_price: float | None = Field(default=None, ge=0)
    monthly_rental_price: float | None = Field(default=None, ge=0)
    replacement_cost_price: float | None = Field(default=None, ge=0)
    min_sale_price: float | None = Field(default=None, ge=0)
    grid_greenwind_price: float | None = Field(default=None, ge=0)
    grid_shengjing_price: float | None = Field(default=None, ge=0)
    package_conversion_enabled: bool | None = None
    status: str | None = Field(default=None, max_length=16)


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ProductVariantBase(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    specification: str = Field(default="", max_length=255)
    specification_values: str = ""
    image_url: str = ""
    unit: str = Field(default="盆", max_length=32)
    is_default: bool = False
    sort_order: int = 100
    conversion_quantity: float = Field(default=1, gt=0)
    reference_purchase_price: float = Field(default=0, ge=0)
    sale_price: float = Field(default=0, ge=0)
    monthly_rental_price: float = Field(default=0, ge=0)
    replacement_cost_price: float = Field(default=0, ge=0)
    min_sale_price: float = Field(default=0, ge=0)
    grid_greenwind_price: float = Field(default=0, ge=0)
    grid_shengjing_price: float = Field(default=0, ge=0)
    stock: float = Field(default=0, ge=0)
    status: str = Field(default="启用", max_length=16)


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    specification: str | None = Field(default=None, max_length=255)
    specification_values: str | None = None
    image_url: str | None = None
    unit: str | None = Field(default=None, max_length=32)
    is_default: bool | None = None
    sort_order: int | None = None
    conversion_quantity: float | None = Field(default=None, gt=0)
    reference_purchase_price: float | None = Field(default=None, ge=0)
    sale_price: float | None = Field(default=None, ge=0)
    monthly_rental_price: float | None = Field(default=None, ge=0)
    replacement_cost_price: float | None = Field(default=None, ge=0)
    min_sale_price: float | None = Field(default=None, ge=0)
    grid_greenwind_price: float | None = Field(default=None, ge=0)
    grid_shengjing_price: float | None = Field(default=None, ge=0)
    stock: float | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, max_length=16)


class ProductVariantRead(ProductVariantBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    created_at: datetime


class PurchaseOrderItemBase(BaseModel):
    product_id: int
    variant_id: int | None = None
    product_name: str = Field(default="", max_length=128)
    variant_name: str = Field(default="", max_length=128)
    quantity: float = Field(default=1, gt=0)
    received_quantity: float = Field(default=0, ge=0)
    unit: str = Field(default="件", max_length=32)
    unit_price: float = Field(default=0, ge=0)
    notes: str = ""


class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    pass


class PurchaseOrderItemRead(PurchaseOrderItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    created_at: datetime


class PurchaseOrderBase(BaseModel):
    order_no: str = Field(min_length=1, max_length=64)
    supplier: str = Field(default="", max_length=128)
    purchaser: str = Field(default="", max_length=64)
    purchase_date: date | None = None
    delivery_method: str = Field(default="入库", max_length=32)
    freight_fee: float = Field(default=0, ge=0)
    hll_fee: float = Field(default=0, ge=0)
    status: str = Field(default="待采购", max_length=16)
    notes: str = ""


class PurchaseOrderCreate(PurchaseOrderBase):
    items: list[PurchaseOrderItemCreate] = Field(default_factory=list)


class PurchaseOrderUpdate(BaseModel):
    order_no: str | None = Field(default=None, min_length=1, max_length=64)
    supplier: str | None = Field(default=None, max_length=128)
    purchaser: str | None = Field(default=None, max_length=64)
    purchase_date: date | None = None
    delivery_method: str | None = Field(default=None, max_length=32)
    freight_fee: float | None = Field(default=None, ge=0)
    hll_fee: float | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, max_length=16)
    notes: str | None = None
    items: list[PurchaseOrderItemCreate] | None = None


class PurchaseOrderRead(PurchaseOrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    items: list[PurchaseOrderItemRead] = Field(default_factory=list)


class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    customer_type: str = Field(default="普通客户", max_length=64)
    project_name: str = Field(default="", max_length=128)
    area: str = Field(default="", max_length=64)
    supervisor_name: str = Field(default="", max_length=64)
    supervisor_phone: str = Field(default="", max_length=32)
    contact_person: str = Field(default="", max_length=64)
    phone: str = Field(default="", max_length=32)
    maintainer_name: str = Field(default="", max_length=64)
    maintainer_phone: str = Field(default="", max_length=32)
    address: str = Field(default="", max_length=255)
    status: str = Field(default="启用", max_length=16)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    customer_type: str | None = Field(default=None, max_length=64)
    project_name: str | None = Field(default=None, max_length=128)
    area: str | None = Field(default=None, max_length=64)
    supervisor_name: str | None = Field(default=None, max_length=64)
    supervisor_phone: str | None = Field(default=None, max_length=32)
    contact_person: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    maintainer_name: str | None = Field(default=None, max_length=64)
    maintainer_phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=16)


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class CustomerAreaSettingBase(BaseModel):
    area: str = Field(min_length=1, max_length=64)
    supervisor_name: str = Field(default="", max_length=64)
    supervisor_phone: str = Field(default="", max_length=32)
    status: str = Field(default="启用", max_length=16)


class CustomerAreaSettingCreate(CustomerAreaSettingBase):
    pass


class CustomerAreaSettingUpdate(BaseModel):
    area: str | None = Field(default=None, min_length=1, max_length=64)
    supervisor_name: str | None = Field(default=None, max_length=64)
    supervisor_phone: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=16)


class CustomerAreaSettingRead(CustomerAreaSettingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class EmployeeBase(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    phone: str = Field(default="", max_length=32)
    position: str = Field(default="", max_length=64)
    role: str = Field(default="员工", max_length=64)
    department: str = Field(default="", max_length=64)
    business_roles: str = Field(default="", max_length=255)
    module_permissions: str = ""
    product_category_permissions: str = ""
    hire_date: date | None = None
    leave_date: date | None = None
    login_enabled: bool = False
    responsibility: str = ""
    status: str = Field(default="在职", max_length=16)


class EmployeeCreate(EmployeeBase):
    login_password: str | None = Field(default=None, min_length=6, max_length=128)


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    position: str | None = Field(default=None, max_length=64)
    role: str | None = Field(default=None, max_length=64)
    department: str | None = Field(default=None, max_length=64)
    business_roles: str | None = Field(default=None, max_length=255)
    module_permissions: str | None = None
    product_category_permissions: str | None = None
    hire_date: date | None = None
    leave_date: date | None = None
    login_enabled: bool | None = None
    responsibility: str | None = None
    status: str | None = Field(default=None, max_length=16)
    login_password: str | None = Field(default=None, min_length=6, max_length=128)


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ProjectBase(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    customer_id: int
    name: str = Field(min_length=1, max_length=128)
    address: str = Field(default="", max_length=255)
    business_types: str = Field(default="租摆", max_length=255)
    plant_source: str = Field(default="新采购", max_length=32)
    supervisor_id: int | None = None
    customer_service_id: int | None = None
    start_date: date | None = None
    status: str = Field(default="进行中", max_length=16)
    notes: str = ""


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    customer_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=128)
    address: str | None = Field(default=None, max_length=255)
    business_types: str | None = Field(default=None, max_length=255)
    plant_source: str | None = Field(default=None, max_length=32)
    supervisor_id: int | None = None
    customer_service_id: int | None = None
    start_date: date | None = None
    status: str | None = Field(default=None, max_length=16)
    notes: str | None = None


class ProjectRead(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str = ""
    supervisor_name: str = ""
    customer_service_name: str = ""
    created_at: datetime


class ProjectContactBase(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    phone: str = Field(default="", max_length=32)
    position: str = Field(default="", max_length=64)
    contact_type: str = Field(default="项目负责人", max_length=32)
    priority: int = Field(default=1, ge=1)
    notes: str = Field(default="", max_length=255)


class ProjectContactCreate(ProjectContactBase):
    pass


class ProjectContactRead(ProjectContactBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int


class ProjectLocationBase(BaseModel):
    parent_id: int | None = None
    name: str = Field(min_length=1, max_length=128)
    location_type: str = Field(default="区域", max_length=32)
    sort_order: int = 0


class ProjectLocationCreate(ProjectLocationBase):
    pass


class ProjectLocationRead(ProjectLocationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int


class ProjectMaintainerBase(BaseModel):
    employee_id: int
    area_description: str = Field(default="全部区域", max_length=255)
    is_primary: bool = False
    start_date: date | None = None
    end_date: date | None = None
    status: str = Field(default="负责中", max_length=16)


class ProjectMaintainerCreate(ProjectMaintainerBase):
    pass


class ProjectMaintainerRead(ProjectMaintainerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    employee_name: str = ""
    employee_phone: str = ""


class ContractBase(BaseModel):
    project_id: int
    contract_no: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    contract_type: str = Field(default="整体合同", max_length=32)
    business_types: str = Field(default="租摆", max_length=255)
    effective_date: date
    end_date: date
    billing_start_date: date | None = None
    billing_cycle: str = Field(default="月付", max_length=32)
    amount: float = Field(default=0, ge=0)
    reminder_days: int = Field(default=30, ge=0)
    status: str = Field(default="生效", max_length=16)
    notes: str = ""


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    project_id: int | None = None
    contract_no: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    contract_type: str | None = Field(default=None, max_length=32)
    business_types: str | None = Field(default=None, max_length=255)
    effective_date: date | None = None
    end_date: date | None = None
    billing_start_date: date | None = None
    billing_cycle: str | None = Field(default=None, max_length=32)
    amount: float | None = Field(default=None, ge=0)
    reminder_days: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, max_length=16)
    notes: str | None = None


class ContractRead(ContractBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_name: str = ""
    created_at: datetime


class ProjectPlantBase(BaseModel):
    project_id: int
    location_id: int
    product_id: int
    specification: str = Field(default="", max_length=128)
    quantity: float = Field(default=1, gt=0)
    unit: str = Field(default="盆", max_length=32)
    decorative_pot: str = Field(default="", max_length=128)
    source: str = Field(default="新采购", max_length=32)
    maintainer_id: int | None = None
    entry_date: date | None = None
    billing_start_date: date | None = None
    status: str = Field(default="在场", max_length=16)
    notes: str = ""


class ProjectPlantCreate(ProjectPlantBase):
    pass


class ProjectPlantUpdate(BaseModel):
    location_id: int | None = None
    product_id: int | None = None
    specification: str | None = Field(default=None, max_length=128)
    quantity: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=32)
    decorative_pot: str | None = Field(default=None, max_length=128)
    source: str | None = Field(default=None, max_length=32)
    maintainer_id: int | None = None
    entry_date: date | None = None
    billing_start_date: date | None = None
    status: str | None = Field(default=None, max_length=16)
    notes: str | None = None


class ProjectPlantRead(ProjectPlantBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_name: str = ""
    location_name: str = ""
    product_name: str = ""
    maintainer_name: str = ""
    created_at: datetime


class ProjectPlantChangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    plant_id: int | None = None
    location_id: int | None = None
    product_id: int | None = None
    change_type: str
    source_type: str = ""
    source_no: str = ""
    quantity_before: float = 0
    quantity_after: float = 0
    quantity_delta: float = 0
    unit: str = ""
    pot_before: str = ""
    pot_after: str = ""
    operator: str = ""
    notes: str = ""
    project_name: str = ""
    location_name: str = ""
    product_name: str = ""
    created_at: datetime


class ProjectSalaryBase(BaseModel):
    project_id: int
    employee_id: int
    salary_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    amount: float = Field(default=0, ge=0)
    adjustment_reason: str = Field(default="", max_length=255)
    status: str = Field(default="未结算", max_length=16)


class ProjectSalaryCreate(ProjectSalaryBase):
    pass


class ProjectSalaryUpdate(BaseModel):
    amount: float | None = Field(default=None, ge=0)
    adjustment_reason: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=16)


class ProjectSalaryRead(ProjectSalaryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_name: str = ""
    employee_name: str = ""
    created_at: datetime


class VehicleBase(BaseModel):
    plate_no: str = Field(min_length=1, max_length=32)
    vehicle_type: str = Field(default="", max_length=64)
    driver_name: str = Field(default="", max_length=64)
    status: str = Field(default="可用", max_length=16)
    insurance_expiry: date | None = None
    inspection_expiry: date | None = None
    maintenance_due_date: date | None = None
    reminder_days: int = Field(default=30, ge=0, le=365)
    reminder_to: str = Field(default="", max_length=255)
    notes: str = ""


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    plate_no: str | None = Field(default=None, min_length=1, max_length=32)
    vehicle_type: str | None = Field(default=None, max_length=64)
    driver_name: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=16)
    insurance_expiry: date | None = None
    inspection_expiry: date | None = None
    maintenance_due_date: date | None = None
    reminder_days: int | None = Field(default=None, ge=0, le=365)
    reminder_to: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class VehicleRead(VehicleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reminder_status: str = "正常"
    reminder_items: list[str] = []
    created_at: datetime


class ScheduleTaskBase(BaseModel):
    task_no: str = Field(min_length=1, max_length=64)
    schedule_date: date
    task_type: str = Field(default="配送", max_length=32)
    source_type: str = Field(default="手工", max_length=32)
    source_no: str = Field(default="", max_length=64)
    project_name: str = Field(default="", max_length=128)
    address: str = Field(default="", max_length=255)
    driver_id: int | None = None
    assistant_ids: str = ""
    vehicle_id: int | None = None
    planned_start: str = Field(default="", max_length=16)
    planned_end: str = Field(default="", max_length=16)
    item_summary: str = ""
    status: str = Field(default="待发布", max_length=16)
    notes: str = ""


class ScheduleTaskCreate(ScheduleTaskBase):
    pass


class ScheduleTaskUpdate(BaseModel):
    task_no: str | None = Field(default=None, min_length=1, max_length=64)
    schedule_date: date | None = None
    task_type: str | None = Field(default=None, max_length=32)
    source_type: str | None = Field(default=None, max_length=32)
    source_no: str | None = Field(default=None, max_length=64)
    project_name: str | None = Field(default=None, max_length=128)
    address: str | None = Field(default=None, max_length=255)
    driver_id: int | None = None
    assistant_ids: str | None = None
    vehicle_id: int | None = None
    planned_start: str | None = Field(default=None, max_length=16)
    planned_end: str | None = Field(default=None, max_length=16)
    item_summary: str | None = None
    status: str | None = Field(default=None, max_length=16)
    notes: str | None = None


class ScheduleTaskRead(ScheduleTaskBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    driver_name: str = ""
    assistant_names: str = ""
    vehicle_plate_no: str = ""
    created_at: datetime
