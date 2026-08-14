import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import MyWorkbenchView from '../views/MyWorkbenchView.vue'
import MobileLayout from '../layouts/MobileLayout.vue'
import MobileHomeView from '../views/mobile/MobileHomeView.vue'
import MobileTasksView from '../views/mobile/MobileTasksView.vue'
import MobileMaintenanceView from '../views/mobile/MobileMaintenanceView.vue'
import MobileExchangeRequestView from '../views/mobile/MobileExchangeRequestView.vue'
import MobileOrderCreateView from '../views/mobile/MobileOrderCreateView.vue'
import MobileProductCreateView from '../views/mobile/MobileProductCreateView.vue'
import ModuleView from '../views/ModuleView.vue'
import BasicListView from '../views/BasicListView.vue'
import EntityCrudView from '../views/EntityCrudView.vue'
import OrderManagementView from '../views/OrderManagementView.vue'
import ProductCatalogView from '../views/ProductCatalogView.vue'
import PurchaseManagementView from '../views/PurchaseManagementView.vue'
import OutboundManagementView from '../views/OutboundManagementView.vue'
import ScheduleManagementView from '../views/ScheduleManagementView.vue'
import SystemSettingsView from '../views/SystemSettingsView.vue'
import ReportSummaryView from '../views/ReportSummaryView.vue'
import OperationCenterView from '../views/OperationCenterView.vue'
import OperationLogsView from '../views/OperationLogsView.vue'
import ForbiddenView from '../views/ForbiddenView.vue'
import AppLayout from '../layouts/AppLayout.vue'

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

const routes = [
  { path: '/login', component: LoginView, meta: { public: true } },
  {
    path: '/mobile',
    component: MobileLayout,
    children: [
      { path: '', name: 'mobile-home', component: MobileHomeView, meta: { title: '移动首页', mobile: true } },
      { path: 'order/new', name: 'mobile-order-new', component: MobileOrderCreateView, meta: { title: '手机下单', mobile: true } },
      { path: 'goods/new', name: 'mobile-goods-new', component: MobileProductCreateView, meta: { title: '新建商品', mobile: true } },
      { path: 'tasks', name: 'mobile-tasks', component: MobileTasksView, meta: { title: '移动任务', mobile: true } },
      { path: 'exchange', name: 'mobile-exchange', component: MobileExchangeRequestView, meta: { title: '手机报单', mobile: true } },
      { path: 'maintenance', name: 'mobile-maintenance', component: MobileMaintenanceView, meta: { title: '移动养护', mobile: true } },
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
      { path: 'projects', name: 'projects', component: BasicListView, meta: { title: title.projects, endpoint: '/projects', permission: 'projects', columns: [
        { prop: 'code', label: '项目编号', width: 120 }, { prop: 'name', label: '项目名称', minWidth: 180 }, { prop: 'customer_name', label: '客户', minWidth: 140 }, { prop: 'business_types', label: '业务类型', minWidth: 130 }, { prop: 'supervisor_name', label: '主管', width: 100 }, { prop: 'status', label: '状态', width: 90 }, { prop: 'address', label: '地址', minWidth: 220 },
      ] } },
      { path: 'staff', name: 'staff', component: EntityCrudView, meta: { title: title.staff, entity: 'employee', permission: 'staff' } },
      { path: 'module/order/:orderType', name: 'order-management', component: OrderManagementView, meta: { title: title.orders, permission: 'orders' } },
      { path: 'module/purchase/list', name: 'purchase-list', component: PurchaseManagementView, meta: { title: title.purchase, permission: 'purchase_inventory' } },
      { path: 'module/warehouse/list', name: 'warehouse-list', component: OutboundManagementView, meta: { title: title.outbound, permission: 'orders' } },
      { path: 'module/schedule/list', name: 'schedule-list', component: ScheduleManagementView, meta: { title: title.schedule, permission: 'schedule_workflow' } },
      { path: 'module/system/settings', name: 'system-settings', component: SystemSettingsView, meta: { title: title.settings, permission: 'system' } },
      { path: 'module/system/logs', name: 'operation-logs', component: OperationLogsView, meta: { title: title.operationLogs, permission: 'system' } },
      { path: 'module/report/:reportType', name: 'report-summary', component: ReportSummaryView, meta: { title: title.projectCost, permission: 'reports' } },
      { path: 'module/operation/center', name: 'operation-center', component: OperationCenterView, meta: { title: title.operationCenter, permission: 'dashboard' } },

      { path: 'module/purchase/my', name: 'my-purchase', component: BasicListView, meta: { title: title.myPurchase, endpoint: '/purchases/my', permission: 'purchase_inventory', columns: [
        { prop: 'purchase_no', label: '采购单号', width: 145 }, { prop: 'source_order_no', label: '来源订单', width: 145 }, { prop: 'project_name', label: '项目', minWidth: 160 }, { prop: 'status', label: '状态', width: 100 }, { prop: 'supplier', label: '供应商', minWidth: 120 }, { prop: 'total_amount', label: '金额', width: 100 },
      ] } },
      { path: 'module/inventory/inbound', name: 'my-inbound', component: BasicListView, meta: { title: title.myInbound, endpoint: '/purchases/inbound', permission: 'purchase_inventory', columns: [
        { prop: 'purchase_no', label: '采购单号', width: 145 }, { prop: 'project_name', label: '项目', minWidth: 160 }, { prop: 'status', label: '状态', width: 100 }, { prop: 'supplier', label: '供应商', minWidth: 120 }, { prop: 'total_amount', label: '金额', width: 100 },
      ] } },
      { path: 'module/inventory/check', name: 'inventory-check', component: BasicListView, meta: { title: title.inventory, endpoint: '/inventory', permission: 'purchase_inventory', columns: [
        { prop: 'product_code', label: '商品编码', width: 130 }, { prop: 'product_name', label: '商品名称', minWidth: 170 }, { prop: 'category', label: '分类', width: 100 }, { prop: 'specification', label: '规格', minWidth: 160 }, { prop: 'unit', label: '单位', width: 80 }, { prop: 'quantity', label: '库存', width: 100 },
      ] } },
      { path: 'module/system/admins', name: 'system-users', component: BasicListView, meta: { title: title.systemUsers, endpoint: '/system/users', permission: 'system', columns: [
        { prop: 'username', label: '账号', width: 140 }, { prop: 'display_name', label: '姓名', width: 120 }, { prop: 'role', label: '角色', width: 100 }, { prop: 'is_active', label: '启用', width: 80 }, { prop: 'module_permissions', label: '模块权限', minWidth: 220 }, { prop: 'product_category_permissions', label: '商品分类权限', minWidth: 220 },
      ] } },
      { path: 'module/vehicle/list', name: 'vehicle-list', component: BasicListView, meta: { title: title.vehicle, endpoint: '/vehicles', permission: 'vehicle', columns: [
        { prop: 'plate_no', label: '车牌号', width: 130 }, { prop: 'vehicle_type', label: '车辆类型', width: 120 }, { prop: 'driver_name', label: '默认司机', width: 110 }, { prop: 'status', label: '状态', width: 100 }, { prop: 'inspection_date', label: '年检日期', width: 120 }, { prop: 'insurance_date', label: '保险日期', width: 120 }, { prop: 'notes', label: '备注', minWidth: 180 },
      ] } },
      { path: 'module/maintenance/manage', name: 'maintenance-manage', component: BasicListView, meta: { title: title.maintenanceManage, endpoint: '/maintenance/plans', permission: 'schedule_workflow', columns: [
        { prop: 'plan_no', label: '计划编号', width: 140 }, { prop: 'project_name', label: '项目', minWidth: 160 }, { prop: 'maintainer_name', label: '养护员', width: 110 }, { prop: 'content', label: '内容', minWidth: 220 }, { prop: 'status', label: '状态', width: 100 },
      ] } },
      { path: 'module/workflow/progress', name: 'workflow-progress', component: BasicListView, meta: { title: title.workflow, endpoint: '/workflows/requests', permission: 'schedule_workflow', columns: [
        { prop: 'request_no', label: '审批编号', width: 145 }, { prop: 'source_no', label: '来源单号', width: 145 }, { prop: 'project_name', label: '项目', minWidth: 160 }, { prop: 'applicant', label: '申请人', width: 100 }, { prop: 'status', label: '状态', width: 100 }, { prop: 'reason', label: '原因', minWidth: 220 },
      ] } },
      { path: 'module/finance/receivable', name: 'receivable-management', component: BasicListView, meta: { title: title.receivable, endpoint: '/finance/receivables', permission: 'finance', columns: [
        { prop: 'receivable_no', label: '应收编号', width: 145 }, { prop: 'project_name', label: '项目', minWidth: 160 }, { prop: 'contract_no', label: '合同编号', width: 130 }, { prop: 'billing_period', label: '账期', width: 120 }, { prop: 'amount', label: '金额', width: 100 }, { prop: 'status', label: '状态', width: 100 },
      ] } },
      { path: 'module/finance/contract', name: 'contract-management', component: BasicListView, meta: { title: title.contract, endpoint: '/contracts', permission: 'finance', columns: [
        { prop: 'contract_no', label: '合同编号', width: 145 }, { prop: 'name', label: '合同名称', minWidth: 180 }, { prop: 'project_name', label: '项目', minWidth: 160 }, { prop: 'business_types', label: '业务', minWidth: 120 }, { prop: 'amount', label: '金额', width: 100 }, { prop: 'status', label: '状态', width: 100 },
      ] } },
      { path: 'module/finance/receipt', name: 'finance-receipts', component: BasicListView, meta: { title: '收款单', endpoint: '/finance/receipts', permission: 'finance', columns: [
        { prop: 'receipt_no', label: '收款编号', width: 145 }, { prop: 'project_name', label: '项目', minWidth: 160 }, { prop: 'payer_name', label: '付款方', minWidth: 140 }, { prop: 'amount', label: '金额', width: 100 }, { prop: 'receipt_date', label: '收款日期', width: 120 },
      ] } },
      { path: 'module/finance/invoice', name: 'finance-invoices', component: BasicListView, meta: { title: '发票管理', endpoint: '/finance/invoices', permission: 'finance', columns: [
        { prop: 'invoice_no', label: '发票编号', width: 145 }, { prop: 'project_name', label: '项目', minWidth: 160 }, { prop: 'invoice_type', label: '类型', width: 110 }, { prop: 'amount', label: '金额', width: 100 }, { prop: 'status', label: '状态', width: 100 },
      ] } },
      { path: 'module/finance/:financeType', name: 'finance-records', component: BasicListView, meta: { title: title.finance, endpoint: '/finance/summary', permission: 'finance', columns: [
        { prop: 'name', label: '名称', minWidth: 160 }, { prop: 'amount', label: '金额', width: 120 }, { prop: 'status', label: '状态', width: 120 },
      ] } },
      { path: 'module/report/project-cost', redirect: '/module/report/profit' },
      { path: 'module/operation/attachments', name: 'attachment-center', component: BasicListView, meta: { title: title.attachments, endpoint: '/attachments', permission: 'dashboard', columns: [
        { prop: 'file_name', label: '文件名', minWidth: 200 }, { prop: 'target_type', label: '关联类型', width: 110 }, { prop: 'target_name', label: '关联名称', minWidth: 160 }, { prop: 'uploader_name', label: '上传人', width: 100 }, { prop: 'created_at', label: '上传时间', width: 170 },
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

function canAccess(permission: unknown) {
  if (!permission) return true
  const saved = localStorage.getItem('greenwind_user')
  const user = saved ? JSON.parse(saved) : null
  const roles = String(user?.role || '').replace('，', ',').split(',').map((item) => item.trim()).filter(Boolean)
  if (roles.some((role) => fullRoles.includes(role))) return true
  const permissions = Array.isArray(user?.module_permissions) ? user.module_permissions : []
  if (!permissions.length) return true
  return permissions.includes(String(permission))
}

router.beforeEach((to) => {
  const token = localStorage.getItem('greenwind_token')
  if (!to.meta.public && !token) return '/login'
  if (to.path === '/login' && token) return '/'
  if (to.name !== 'forbidden' && !canAccess(to.meta.permission)) return '/403'
})

export default router
