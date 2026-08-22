import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import MobileLoginView from '../views/mobile/MobileLoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import MyWorkbenchView from '../views/MyWorkbenchView.vue'
import MobileLayout from '../layouts/MobileLayout.vue'
import MobileHomeView from '../views/mobile/MobileHomeView.vue'
import MobileTasksView from '../views/mobile/MobileTasksView.vue'
import MobileMaintenanceView from '../views/mobile/MobileMaintenanceView.vue'
import MobileExchangeRequestView from '../views/mobile/MobileExchangeRequestView.vue'
import MobileOrderCreateView from '../views/mobile/MobileOrderCreateView.vue'
import MobileProductCreateView from '../views/mobile/MobileProductCreateView.vue'
import MobilePurchaseView from '../views/mobile/MobilePurchaseView.vue'
import MobileInventoryView from '../views/mobile/MobileInventoryView.vue'
import MobileOutboundView from '../views/mobile/MobileOutboundView.vue'
import MobileDirectoryView from '../views/mobile/MobileDirectoryView.vue'
import ModuleView from '../views/ModuleView.vue'
import BasicListView from '../views/BasicListView.vue'
import EntityCrudView from '../views/EntityCrudView.vue'
import ProjectManagementView from '../views/ProjectManagementView.vue'
import OrderManagementView from '../views/OrderManagementView.vue'
import ProductCatalogView from '../views/ProductCatalogView.vue'
import PurchaseManagementView from '../views/PurchaseManagementView.vue'
import ReceiptInboundView from '../views/ReceiptInboundView.vue'
import OutboundManagementView from '../views/OutboundManagementView.vue'
import InventoryManagementView from '../views/InventoryManagementView.vue'
import ScheduleManagementView from '../views/ScheduleManagementView.vue'
import SystemSettingsView from '../views/SystemSettingsView.vue'
import ReportSummaryView from '../views/ReportSummaryView.vue'
import OperationCenterView from '../views/OperationCenterView.vue'
import OperationLogsView from '../views/OperationLogsView.vue'
import ForbiddenView from '../views/ForbiddenView.vue'
import AppLayout from '../layouts/AppLayout.vue'
import { useAuthStore } from '../stores/auth'

const title = {
  dashboard: '首页工作台',
  myWorkbench: '我的工作台',
  goods: '商品管理',
  customers: '客户管理',
  projects: '项目管理',
  staff: '员工管理',
  orders: '订单管理',
  purchase: '采购单',
  myPurchase: '我的采购任务',
  myInbound: '入库任务',
  inventory: '库存管理',
  outbound: '配送单',
  settings: '平台设置',
  vehicle: '车辆管理',
  schedule: '每日安排表',
  workflow: '审批进度',
  projectCost: '项目成本中心',
  finance: '财务管理',
  contract: '合同管理',
  receivable: '应收账期',
  operationCenter: '运营提醒中心',
  attachments: '资料附件中心',
  maintenanceManage: '养护管理',
  operationLogs: '操作日志',
  systemUsers: '账号权限',
}

const businessTypeOptions = ['租摆', '工程绿化', '电网', '保洁', '销售', '换花', '赠送', '撤花', '室外养护', '工程养护']
const projectOptions = { optionEndpoint: '/projects', optionLabel: 'name', optionValue: 'id' }
const customerOptions = { optionEndpoint: '/customers', optionLabel: 'name', optionValue: 'id' }
const employeeOptions = { optionEndpoint: '/employees', optionLabel: 'name', optionValue: 'id' }
const contractOptions = { optionEndpoint: '/contracts', optionLabel: 'contract_no', optionValue: 'id' }
const invoiceOptions = { optionEndpoint: '/finance/invoices', optionLabel: 'invoice_no', optionValue: 'id' }
const modulePermissionOptions = ['dashboard', 'orders', 'purchase_inventory', 'customers', 'projects', 'goods', 'staff', 'finance', 'reports', 'vehicle', 'schedule_workflow', 'system']

const routes = [
  { path: '/login', component: LoginView, meta: { public: true } },
  { path: '/mobile/login', component: MobileLoginView, meta: { public: true, mobile: true, title: '移动端登录' } },
  {
    path: '/mobile',
    component: MobileLayout,
    meta: { mobile: true },
    children: [
      { path: '', name: 'mobile-home', component: MobileHomeView, meta: { title: '移动首页', mobile: true } },
      { path: 'order/new', name: 'mobile-order-new', component: MobileOrderCreateView, meta: { title: '手机下单', mobile: true } },
      { path: 'goods/new', name: 'mobile-goods-new', component: MobileProductCreateView, meta: { title: '新建商品', mobile: true } },
      { path: 'tasks', name: 'mobile-tasks', component: MobileTasksView, meta: { title: '移动任务', mobile: true } },
      { path: 'exchange', name: 'mobile-exchange', component: MobileExchangeRequestView, meta: { title: '手机报单', mobile: true } },
      { path: 'maintenance', name: 'mobile-maintenance', component: MobileMaintenanceView, meta: { title: '移动养护', mobile: true } },
      { path: 'purchases', name: 'mobile-purchases', component: MobilePurchaseView, meta: { title: '移动采购', mobile: true } },
      { path: 'inventory', name: 'mobile-inventory', component: MobileInventoryView, meta: { title: '库存余量', mobile: true } },
      { path: 'outbound', name: 'mobile-outbound', component: MobileOutboundView, meta: { title: '仓库配货', mobile: true } },
      { path: 'list/:module', name: 'mobile-directory', component: MobileDirectoryView, meta: { title: '移动查询', mobile: true } },
    ],
  },
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', name: 'dashboard', component: DashboardView, meta: { title: title.dashboard, permission: 'dashboard' } },
      { path: 'module/workbench/my', name: 'my-workbench', component: MyWorkbenchView, meta: { title: title.myWorkbench, permission: 'dashboard' } },
      { path: '403', name: 'forbidden', component: ForbiddenView, meta: { title: '无权限' } },
      { path: 'goods', name: 'goods', component: ProductCatalogView, meta: { title: title.goods, permission: 'goods' } },
      { path: 'customers', name: 'customers', component: EntityCrudView, meta: { title: title.customers, entity: 'customer', permission: 'customers' } },
      { path: 'projects', name: 'projects', component: ProjectManagementView, meta: { title: title.projects, permission: 'projects' } },
      { path: 'staff', name: 'staff', component: EntityCrudView, meta: { title: title.staff, entity: 'employee', permission: 'staff' } },
      { path: 'module/order/:orderType', name: 'order-management', component: OrderManagementView, meta: { title: title.orders, permission: 'orders' } },
      { path: 'module/purchase/list', name: 'purchase-list', component: PurchaseManagementView, meta: { title: title.purchase, permission: 'purchase_inventory' } },
      { path: 'module/purchase/receipts', name: 'purchase-receipts', component: ReceiptInboundView, meta: { title: '收据入库', permission: 'purchase_inventory' } },
      { path: 'module/warehouse/list', name: 'warehouse-list', component: OutboundManagementView, meta: { title: title.outbound, permission: 'orders' } },
      { path: 'module/warehouse/outbound', name: 'warehouse-outbound', component: OutboundManagementView, meta: { title: '出库记录', permission: 'purchase_inventory' } },
      { path: 'module/schedule/list', name: 'schedule-list', component: ScheduleManagementView, meta: { title: title.schedule, permission: 'schedule_workflow' } },
      { path: 'module/schedule/daily', name: 'schedule-daily', component: ScheduleManagementView, meta: { title: title.schedule, permission: 'schedule_workflow' } },
      { path: 'module/system/settings', name: 'system-settings', component: SystemSettingsView, meta: { title: title.settings, permission: 'system' } },
      { path: 'module/system/logs', name: 'operation-logs', component: OperationLogsView, meta: { title: title.operationLogs, permission: 'system' } },
      { path: 'module/report/:reportType', name: 'report-summary', component: ReportSummaryView, meta: { title: title.projectCost, permission: 'reports' } },
      { path: 'module/operation/center', name: 'operation-center', component: OperationCenterView, meta: { title: title.operationCenter, permission: 'dashboard' } },

      { path: 'module/purchase/my', name: 'my-purchase', component: BasicListView, meta: { title: title.myPurchase, endpoint: '/purchases/my', updateEndpoint: '/purchases', permission: 'purchase_inventory', canEdit: true, columns: [
        { prop: 'order_no', label: '采购单号', width: 145 }, { prop: 'source_order_no', label: '来源订单', width: 145 }, { prop: 'status', label: '状态', width: 100 }, { prop: 'supplier', label: '供应商', minWidth: 120 }, { prop: 'purchaser', label: '采购员', width: 110 }, { prop: 'total_amount', label: '金额', width: 100 },
      ], formFields: [
        { key: 'supplier', label: '供应商' },
        { key: 'purchaser', label: '采购员' },
        { key: 'purchase_date', label: '采购日期', type: 'date' },
        { key: 'delivery_method', label: '到货方式', type: 'select', options: ['入库', '货拉拉', '快递', '客户自提'], default: '入库' },
        { key: 'freight_fee', label: '运费', type: 'number' },
        { key: 'hll_fee', label: '货拉拉费用', type: 'number' },
        { key: 'status', label: '状态', type: 'select', options: ['待采购', '采购中', '待入库', '已入库'], default: '待采购' },
        { key: 'notes', label: '备注', type: 'textarea', full: true },
      ], rowActions: [
        { label: '采购完成', type: 'success', endpoint: '/purchases/{id}/mark-purchased', confirm: '确认该采购单已完成采购，并流转到待入库吗？' },
      ] } },
      { path: 'module/inventory/inbound', name: 'my-inbound', component: BasicListView, meta: { title: title.myInbound, endpoint: '/purchases/inbound', updateEndpoint: '/purchases', permission: 'purchase_inventory', canEdit: true, columns: [
        { prop: 'order_no', label: '采购单号', width: 145 }, { prop: 'status', label: '状态', width: 100 }, { prop: 'supplier', label: '供应商', minWidth: 120 }, { prop: 'purchaser', label: '采购员', width: 110 }, { prop: 'total_amount', label: '金额', width: 100 }, { prop: 'purchase_date', label: '采购日期', width: 120 },
      ], formFields: [
        { key: 'supplier', label: '供应商' },
        { key: 'purchaser', label: '采购员' },
        { key: 'purchase_date', label: '采购日期', type: 'date' },
        { key: 'freight_fee', label: '运费', type: 'number' },
        { key: 'hll_fee', label: '货拉拉费用', type: 'number' },
        { key: 'notes', label: '备注', type: 'textarea', full: true },
      ], rowActions: [
        { label: '确认入库', type: 'success', endpoint: '/purchases/{id}/receive', confirm: '确认采购货品已入库吗？' },
      ] } },
      { path: 'module/inventory/check', name: 'inventory-check', component: InventoryManagementView, meta: { title: title.inventory, permission: 'purchase_inventory', columns: [
        { prop: 'variant_code', label: '规格编码', width: 160 }, { prop: 'product_code', label: '商品编码', width: 140 }, { prop: 'product_name', label: '商品名称', minWidth: 170 }, { prop: 'category', label: '分类', width: 100 }, { prop: 'specification', label: '规格', minWidth: 160 }, { prop: 'unit', label: '单位', width: 80 }, { prop: 'stock', label: '库存', width: 100 }, { prop: 'reference_purchase_price', label: '最新采购价', width: 120 }, { prop: 'status', label: '状态', width: 90 },
      ] } },
      { path: 'module/system/admins', name: 'system-users', component: BasicListView, meta: { title: title.systemUsers, endpoint: '/system/users', permission: 'system', canCreate: true, canEdit: true, columns: [
        { prop: 'username', label: '账号', width: 140 }, { prop: 'display_name', label: '姓名', width: 120 }, { prop: 'role', label: '角色', width: 100 }, { prop: 'is_active', label: '启用', width: 80 }, { prop: 'module_permissions', label: '模块权限', minWidth: 220 }, { prop: 'product_category_permissions', label: '商品分类权限', minWidth: 220 },
      ], formFields: [
        { key: 'username', label: '登录账号/手机号', required: true, createOnly: true },
        { key: 'display_name', label: '姓名', required: true },
        { key: 'role', label: '角色', type: 'select', options: ['管理员', '经理', '主管', '客服', '采购', '仓管', '养护员', '司机', '跟车配送', '财务'], default: '员工' },
        { key: 'module_permissions', label: '模块权限', type: 'multi-select', options: modulePermissionOptions, full: true },
        { key: 'product_category_permissions', label: '商品分类权限', placeholder: '多个分类用逗号隔开', full: true },
        { key: 'password', label: '登录密码', type: 'password', placeholder: '新增必填；编辑时留空表示不修改' },
        { key: 'is_active', label: '允许登录', type: 'switch', default: true },
      ] } },
      { path: 'module/vehicle/list', name: 'vehicle-list', component: BasicListView, meta: { title: title.vehicle, endpoint: '/vehicles', permission: 'vehicle', canCreate: true, canEdit: true, canDelete: true, columns: [
        { prop: 'plate_no', label: '车牌号', width: 130 }, { prop: 'vehicle_type', label: '车辆类型', width: 120 }, { prop: 'driver_name', label: '默认司机', width: 110 }, { prop: 'status', label: '状态', width: 100 }, { prop: 'inspection_expiry', label: '年检到期', width: 120 }, { prop: 'insurance_expiry', label: '保险到期', width: 120 }, { prop: 'maintenance_due_date', label: '保养日期', width: 120 }, { prop: 'reminder_status', label: '提醒', width: 100 }, { prop: 'notes', label: '备注', minWidth: 180 },
      ], formFields: [
        { key: 'plate_no', label: '车牌号', required: true },
        { key: 'vehicle_type', label: '车辆类型' },
        { key: 'driver_name', label: '默认司机' },
        { key: 'status', label: '状态', type: 'select', options: ['可用', '维修中', '停用'], default: '可用' },
        { key: 'insurance_expiry', label: '保险到期', type: 'date' },
        { key: 'inspection_expiry', label: '年检到期', type: 'date' },
        { key: 'maintenance_due_date', label: '保养日期', type: 'date' },
        { key: 'reminder_days', label: '提前提醒天数', type: 'number', default: 30 },
        { key: 'reminder_to', label: '提醒给谁' },
        { key: 'notes', label: '备注', type: 'textarea', full: true },
      ] } },
      { path: 'module/maintenance/manage', name: 'maintenance-manage', component: BasicListView, meta: { title: title.maintenanceManage, endpoint: '/maintenance/plans', permission: 'schedule_workflow', canCreate: true, canEdit: true, columns: [
        { prop: 'plan_no', label: '计划编号', width: 140 }, { prop: 'project_name', label: '项目', minWidth: 160 }, { prop: 'maintainer_name', label: '养护员', width: 110 }, { prop: 'area_description', label: '养护区域', minWidth: 160 }, { prop: 'service_content', label: '内容', minWidth: 220 }, { prop: 'next_due_date', label: '下次日期', width: 120 }, { prop: 'status', label: '状态', width: 100 },
      ], formFields: [
        { key: 'plan_no', label: '计划编号', placeholder: '留空自动生成' },
        { key: 'project_id', label: '项目', type: 'select', required: true, ...projectOptions },
        { key: 'maintainer_id', label: '养护员', type: 'select', ...employeeOptions },
        { key: 'area_description', label: '养护区域', default: '全部区域' },
        { key: 'frequency_type', label: '频率类型', type: 'select', options: ['每周次数', '每月次数', '固定日期', '临时'], default: '每月次数' },
        { key: 'frequency_value', label: '频率说明' },
        { key: 'start_date', label: '开始日期', type: 'date' },
        { key: 'end_date', label: '结束日期', type: 'date' },
        { key: 'next_due_date', label: '下次养护日期', type: 'date' },
        { key: 'reminder_days', label: '提前提醒天数', type: 'number', default: 2 },
        { key: 'status', label: '状态', type: 'select', options: ['启用', '暂停', '结束'], default: '启用' },
        { key: 'service_content', label: '养护内容', type: 'textarea', full: true },
        { key: 'notes', label: '备注', type: 'textarea', full: true },
      ] } },
      { path: 'module/workflow/progress', name: 'workflow-progress', component: BasicListView, meta: { title: title.workflow, endpoint: '/workflows/requests', permission: 'schedule_workflow', canCreate: true, columns: [
        { prop: 'request_no', label: '审批编号', width: 145 }, { prop: 'approval_type', label: '审批类型', width: 120 }, { prop: 'source_no', label: '来源单号', width: 145 }, { prop: 'project_name', label: '项目', minWidth: 160 }, { prop: 'applicant', label: '申请人', width: 100 }, { prop: 'amount', label: '金额', width: 100 }, { prop: 'status', label: '状态', width: 100 }, { prop: 'reason', label: '原因', minWidth: 220 },
      ], formFields: [
        { key: 'request_no', label: '审批编号', placeholder: '留空自动生成' },
        { key: 'approval_type', label: '审批类型', type: 'select', options: ['采购审批', '换花审批', '费用审批', '手工审批'], default: '手工审批' },
        { key: 'source_type', label: '来源类型', default: '手工' },
        { key: 'source_no', label: '来源单号' },
        { key: 'project_id', label: '项目', type: 'select', ...projectOptions },
        { key: 'applicant', label: '申请人' },
        { key: 'amount', label: '金额', type: 'number' },
        { key: 'approver_role', label: '审批角色', default: '经理' },
        { key: 'approver_name', label: '审批人' },
        { key: 'reason', label: '申请原因', type: 'textarea', full: true },
      ], rowActions: [
        { label: '通过', type: 'success', endpoint: '/workflows/requests/{id}/decision', payload: { status: '已通过' }, confirm: '确认通过这条审批吗？' },
        { label: '驳回', type: 'danger', endpoint: '/workflows/requests/{id}/decision', payload: { status: '已驳回' }, confirm: '确认驳回这条审批吗？' },
      ] } },
      { path: 'module/finance/receivable', name: 'receivable-management', component: BasicListView, meta: { title: title.receivable, endpoint: '/finance/receivables', permission: 'finance', canCreate: true, canEdit: true, canDelete: true, columns: [
        { prop: 'receivable_no', label: '应收编号', width: 145 }, { prop: 'project_name', label: '项目', minWidth: 160 }, { prop: 'contract_no', label: '合同编号', width: 130 }, { prop: 'billing_period', label: '账期', width: 120 }, { prop: 'amount', label: '金额', width: 100 }, { prop: 'received_amount', label: '已收', width: 100 }, { prop: 'invoice_amount', label: '已开票', width: 100 }, { prop: 'status', label: '状态', width: 100 },
      ], formFields: [
        { key: 'receivable_no', label: '应收编号', required: true },
        { key: 'project_id', label: '项目', type: 'select', required: true, ...projectOptions },
        { key: 'contract_id', label: '合同', type: 'select', ...contractOptions },
        { key: 'billing_period', label: '账期' },
        { key: 'due_date', label: '到期日期', type: 'date' },
        { key: 'amount', label: '应收金额', type: 'number', required: true },
        { key: 'receivable_type', label: '应收类型', type: 'select', options: ['合同应收', '临时销售', '工程养护', '其他'], default: '合同应收' },
        { key: 'status', label: '状态', type: 'select', options: ['待收款', '部分收款', '已收款', '逾期', '作废'], default: '待收款' },
        { key: 'notes', label: '备注', type: 'textarea', full: true },
      ] } },
      { path: 'module/finance/contract', name: 'contract-management', component: BasicListView, meta: { title: title.contract, endpoint: '/contracts', permission: 'finance', canCreate: true, canEdit: true, canDelete: true, columns: [
        { prop: 'contract_no', label: '合同编号', width: 145 }, { prop: 'name', label: '合同名称', minWidth: 180 }, { prop: 'project_name', label: '项目', minWidth: 160 }, { prop: 'business_types', label: '业务', minWidth: 120 }, { prop: 'billing_cycle', label: '付款方式', width: 100 }, { prop: 'amount', label: '金额', width: 100 }, { prop: 'status', label: '状态', width: 100 },
      ], formFields: [
        { key: 'project_id', label: '项目', type: 'select', required: true, ...projectOptions },
        { key: 'contract_no', label: '合同编号', required: true },
        { key: 'name', label: '合同名称', required: true },
        { key: 'contract_type', label: '合同类型', type: 'select', options: ['整体合同', '分体合同'], default: '整体合同' },
        { key: 'business_types', label: '业务类型', type: 'multi-select', options: businessTypeOptions, default: ['租摆'] },
        { key: 'effective_date', label: '生效日期', type: 'date', required: true },
        { key: 'end_date', label: '结束日期', type: 'date', required: true },
        { key: 'billing_start_date', label: '计费开始日期', type: 'date' },
        { key: 'billing_cycle', label: '付款方式', type: 'select', options: ['月付', '季付', '半年付', '年付', '一次性'], default: '月付' },
        { key: 'amount', label: '合同金额', type: 'number' },
        { key: 'reminder_days', label: '到期提醒天数', type: 'number', default: 30 },
        { key: 'status', label: '状态', type: 'select', options: ['生效', '待签', '暂停', '到期', '终止'], default: '生效' },
        { key: 'notes', label: '备注', type: 'textarea', full: true },
      ], rowActions: [
        { label: '生成应收', type: 'success', endpoint: '/finance/receivables/generate-from-contract/{id}', confirm: '根据合同生成应收账期吗？' },
      ] } },
      { path: 'module/finance/receipt', name: 'finance-receipts', component: BasicListView, meta: { title: '收款单', endpoint: '/finance/receipts', permission: 'finance', canCreate: true, canEdit: true, canDelete: true, columns: [
        { prop: 'receipt_no', label: '收款编号', width: 145 }, { prop: 'project_name', label: '项目', minWidth: 160 }, { prop: 'invoice_no', label: '发票编号', width: 130 }, { prop: 'payer_name', label: '付款方', minWidth: 140 }, { prop: 'amount', label: '金额', width: 100 }, { prop: 'receipt_date', label: '收款日期', width: 120 }, { prop: 'status', label: '状态', width: 100 },
      ], formFields: [
        { key: 'receipt_no', label: '收款编号', required: true },
        { key: 'project_id', label: '项目', type: 'select', required: true, ...projectOptions },
        { key: 'contract_id', label: '合同', type: 'select', ...contractOptions },
        { key: 'invoice_id', label: '发票', type: 'select', ...invoiceOptions },
        { key: 'receipt_date', label: '收款日期', type: 'date' },
        { key: 'billing_period', label: '账期' },
        { key: 'amount', label: '收款金额', type: 'number', required: true },
        { key: 'payment_method', label: '收款方式', type: 'select', options: ['现金', '微信', '支付宝', '银行转账', '支票'], default: '银行转账' },
        { key: 'payer_name', label: '付款方' },
        { key: 'handler', label: '经办人' },
        { key: 'source_no', label: '来源单号' },
        { key: 'status', label: '状态', type: 'select', options: ['已收款', '待确认', '作废'], default: '已收款' },
        { key: 'notes', label: '备注', type: 'textarea', full: true },
      ] } },
      { path: 'module/finance/invoice', name: 'finance-invoices', component: BasicListView, meta: { title: '发票管理', endpoint: '/finance/invoices', permission: 'finance', canCreate: true, canEdit: true, canDelete: true, columns: [
        { prop: 'invoice_no', label: '发票编号', width: 145 }, { prop: 'project_name', label: '项目', minWidth: 160 }, { prop: 'invoice_type', label: '类型', width: 110 }, { prop: 'payer_name', label: '购方名称', minWidth: 140 }, { prop: 'amount', label: '金额', width: 100 }, { prop: 'invoice_date', label: '开票日期', width: 120 }, { prop: 'status', label: '状态', width: 100 },
      ], formFields: [
        { key: 'invoice_no', label: '发票编号', required: true },
        { key: 'project_id', label: '项目', type: 'select', required: true, ...projectOptions },
        { key: 'contract_id', label: '合同', type: 'select', ...contractOptions },
        { key: 'invoice_date', label: '开票日期', type: 'date' },
        { key: 'billing_period', label: '账期' },
        { key: 'amount', label: '开票金额', type: 'number', required: true },
        { key: 'tax_amount', label: '税额', type: 'number' },
        { key: 'invoice_type', label: '发票类型', type: 'select', options: ['普票', '专票', '电子发票'], default: '普票' },
        { key: 'payer_name', label: '购方名称' },
        { key: 'handler', label: '经办人' },
        { key: 'source_no', label: '来源单号' },
        { key: 'status', label: '状态', type: 'select', options: ['已开票', '待开票', '作废'], default: '已开票' },
        { key: 'notes', label: '备注', type: 'textarea', full: true },
      ] } },
      { path: 'module/finance/:financeType', name: 'finance-records', component: BasicListView, meta: { title: title.finance, endpoint: '/finance/summary', permission: 'finance', columns: [
        { prop: 'name', label: '名称', minWidth: 160 }, { prop: 'amount', label: '金额', width: 120 }, { prop: 'status', label: '状态', width: 120 },
      ] } },
      { path: 'module/report/project-cost', redirect: '/module/report/profit' },
      { path: 'module/operation/attachments', name: 'attachment-center', component: BasicListView, meta: { title: title.attachments, endpoint: '/attachments', permission: 'dashboard', canCreate: true, canDelete: true, columns: [
        { prop: 'file_name', label: '文件名', minWidth: 200 }, { prop: 'target_type', label: '关联类型', width: 110 }, { prop: 'target_name', label: '关联名称', minWidth: 160 }, { prop: 'uploader_name', label: '上传人', width: 100 }, { prop: 'created_at', label: '上传时间', width: 170 },
      ], formFields: [
        { key: 'target_type', label: '关联类型', type: 'select', options: ['项目', '客户', '订单', '采购单', '合同', '车辆', '其他'], default: '其他' },
        { key: 'target_id', label: '关联ID', type: 'number' },
        { key: 'target_name', label: '关联名称' },
        { key: 'file_name', label: '文件名' },
        { key: 'file_size', label: '文件大小', type: 'number' },
        { key: 'file_type', label: '文件类型' },
        { key: 'data_url', label: '上传附件', type: 'file', required: true, full: true },
        { key: 'notes', label: '备注', type: 'textarea', full: true },
      ] } },

      { path: 'module/operation/articles', redirect: '/module/operation/center' },
      { path: 'module/operation/renewal', redirect: '/module/operation/center' },
      { path: 'module/material/:pathMatch(.*)*', redirect: '/goods' },
      { path: 'module/goods/:pathMatch(.*)*', redirect: '/goods' },
      { path: 'module/customer/:pathMatch(.*)*', redirect: '/customers' },
      { path: 'module/staff/:pathMatch(.*)*', redirect: '/staff' },
      { path: 'module/:module/:page?', name: 'module', component: ModuleView },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })
const fullRoles = ['admin', '管理员', '经理', '老板']

function canAccess(permission: unknown, user: Record<string, any> | null) {
  if (!permission) return true
  const roles = String(user?.role || '').replace('，', ',').split(',').map((item) => item.trim()).filter(Boolean)
  if (roles.some((role) => fullRoles.includes(role))) return true
  const permissions = Array.isArray(user?.module_permissions) ? user.module_permissions : []
  if (!permissions.length) return true
  return permissions.includes(String(permission))
}

router.beforeEach((to) => {
  const mobile = to.path.startsWith('/mobile') || to.matched.some((record) => Boolean(record.meta.mobile))
  const auth = useAuthStore()
  auth.activateScope(mobile ? 'mobile' : 'desktop')
  if (!to.meta.public && !auth.token) {
    return { path: mobile ? '/mobile/login' : '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/mobile/login' && auth.token) return '/mobile'
  if (to.path === '/login' && auth.token) return '/'
  if (!mobile && to.name !== 'forbidden' && !canAccess(to.meta.permission, auth.user)) return '/403'
})

export default router
