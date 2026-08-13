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
  dashboard: '工作台',
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
      { path: 'module/order/:orderType', name: 'order-management', component: OrderManagementView, meta: { title: title.orders, permission: 'orders' } },
      { path: 'module/purchase/list', name: 'purchase-list', component: PurchaseManagementView, meta: { title: title.purchase, permission: 'purchase_inventory' } },
      { path: 'module/warehouse/list', name: 'warehouse-list', component: OutboundManagementView, meta: { title: title.outbound, permission: 'orders' } },
      { path: 'module/schedule/list', name: 'schedule-list', component: ScheduleManagementView, meta: { title: title.schedule, permission: 'schedule_workflow' } },
      { path: 'module/system/settings', name: 'system-settings', component: SystemSettingsView, meta: { title: title.settings, permission: 'system' } },
      { path: 'module/system/logs', name: 'operation-logs', component: OperationLogsView, meta: { title: title.operationLogs, permission: 'system' } },
      { path: 'module/report/:reportType', name: 'report-summary', component: ReportSummaryView, meta: { title: title.projectCost, permission: 'reports' } },
      { path: 'module/operation/center', name: 'operation-center', component: OperationCenterView, meta: { title: title.operationCenter, permission: 'dashboard' } },

      // 下面这些页面原源码有乱码导致 Vue 编译失败，先统一进入占位页，系统先可用。
      { path: 'customers', name: 'customers', component: ModuleView, meta: { title: title.customers, permission: 'customers' } },
      { path: 'projects', name: 'projects', component: ModuleView, meta: { title: title.projects, permission: 'projects' } },
      { path: 'staff', name: 'staff', component: ModuleView, meta: { title: title.staff, permission: 'staff' } },
      { path: 'module/purchase/my', name: 'my-purchase', component: ModuleView, meta: { title: title.myPurchase, permission: 'purchase_inventory' } },
      { path: 'module/inventory/inbound', name: 'my-inbound', component: ModuleView, meta: { title: title.myInbound, permission: 'purchase_inventory' } },
      { path: 'module/inventory/check', name: 'inventory-check', component: ModuleView, meta: { title: title.inventory, permission: 'purchase_inventory' } },
      { path: 'module/system/admins', name: 'system-users', component: ModuleView, meta: { title: title.systemUsers, permission: 'system' } },
      { path: 'module/vehicle/list', name: 'vehicle-list', component: ModuleView, meta: { title: title.vehicle, permission: 'vehicle' } },
      { path: 'module/maintenance/manage', name: 'maintenance-manage', component: ModuleView, meta: { title: title.maintenanceManage, permission: 'schedule_workflow' } },
      { path: 'module/workflow/progress', name: 'workflow-progress', component: ModuleView, meta: { title: title.workflow, permission: 'schedule_workflow' } },
      { path: 'module/finance/receivable', name: 'receivable-management', component: ModuleView, meta: { title: title.receivable, permission: 'finance' } },
      { path: 'module/finance/contract', name: 'contract-management', component: ModuleView, meta: { title: title.contract, permission: 'finance' } },
      { path: 'module/finance/:financeType', name: 'finance-records', component: ModuleView, meta: { title: title.finance, permission: 'finance' } },
      { path: 'module/report/project-cost', name: 'project-cost-report', component: ModuleView, meta: { title: title.projectCost, permission: 'reports' } },
      { path: 'module/operation/attachments', name: 'attachment-center', component: ModuleView, meta: { title: title.attachments, permission: 'dashboard' } },

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
