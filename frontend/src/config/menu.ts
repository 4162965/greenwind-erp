import type { Component } from 'vue'
import {
  Briefcase,
  Calendar,
  Coin,
  DataAnalysis,
  Document,
  Goods,
  House,
  MapLocation,
  OfficeBuilding,
  Operation,
  Setting,
  ShoppingCart,
  Tickets,
  User,
  Van,
} from '@element-plus/icons-vue'

export interface MenuItem {
  label: string
  path?: string
  icon?: Component
  children?: MenuItem[]
  permission?: string
}

export const permissionOptions = [
  { label: '工作台', value: 'dashboard' },
  { label: '商品管理', value: 'goods' },
  { label: '订单管理', value: 'orders' },
  { label: '客户管理', value: 'customers' },
  { label: '项目管理', value: 'projects' },
  { label: '采购与仓管', value: 'purchase_inventory' },
  { label: '财务管理', value: 'finance' },
  { label: '报表统计', value: 'reports' },
  { label: '员工管理', value: 'staff' },
  { label: '车辆管理', value: 'vehicle' },
  { label: '配送与养护', value: 'schedule_workflow' },
  { label: '系统设置', value: 'system' },
]

export const menuItems: MenuItem[] = [
  { label: '首页工作台', path: '/', icon: House, permission: 'dashboard' },
  {
    label: '订单管理',
    icon: ShoppingCart,
    permission: 'orders',
    children: [
      { label: '租赁订单', path: '/module/order/lease', permission: 'orders' },
      { label: '销售订单', path: '/module/order/sales', permission: 'orders' },
      { label: '换花订单', path: '/module/order/exchange', permission: 'orders' },
      { label: '赠送订单', path: '/module/order/gift', permission: 'orders' },
      { label: '撤花订单', path: '/module/order/withdraw', permission: 'orders' },
      { label: '配送订单', path: '/module/warehouse/list', permission: 'orders' },
    ],
  },
  {
    label: '采购管理',
    icon: Briefcase,
    permission: 'purchase_inventory',
    children: [
      { label: '采购单', path: '/module/purchase/list', permission: 'purchase_inventory' },
      { label: '我的采购任务', path: '/module/purchase/my', permission: 'purchase_inventory' },
    ],
  },
  {
    label: '仓管管理',
    icon: Goods,
    permission: 'purchase_inventory',
    children: [
      { label: '入库任务', path: '/module/inventory/inbound', permission: 'purchase_inventory' },
      { label: '库存盘点', path: '/module/inventory/check', permission: 'purchase_inventory' },
    ],
  },
  {
    label: '配送管理',
    icon: Van,
    permission: 'schedule_workflow',
    children: [
      { label: '每日安排表', path: '/module/schedule/list', permission: 'schedule_workflow' },
      { label: '车辆管理', path: '/module/vehicle/list', permission: 'vehicle' },
    ],
  },
  {
    label: '养护管理',
    icon: Calendar,
    permission: 'schedule_workflow',
    children: [
      { label: '养护管理', path: '/module/maintenance/manage', permission: 'schedule_workflow' },
      { label: '审批进度', path: '/module/workflow/progress', permission: 'schedule_workflow' },
    ],
  },
  {
    label: '基础资料',
    icon: OfficeBuilding,
    children: [
      { label: '客户资料', path: '/customers', permission: 'customers' },
      { label: '项目资料', path: '/projects', permission: 'projects' },
      { label: '商品资料', path: '/goods', permission: 'goods' },
      { label: '员工资料', path: '/staff', permission: 'staff' },
      { label: '资料附件', path: '/module/operation/attachments', permission: 'dashboard' },
    ],
  },
  {
    label: '财务合同',
    icon: Coin,
    permission: 'finance',
    children: [
      { label: '合同管理', path: '/module/finance/contract', permission: 'finance' },
      { label: '应收账期', path: '/module/finance/receivable', permission: 'finance' },
      { label: '收款单', path: '/module/finance/receipt', permission: 'finance' },
      { label: '发票管理', path: '/module/finance/invoice', permission: 'finance' },
    ],
  },
  {
    label: '报表分析',
    icon: DataAnalysis,
    permission: 'reports',
    children: [
      { label: '项目成本', path: '/module/report/project-cost', permission: 'reports' },
      { label: '订单销量', path: '/module/report/orders', permission: 'reports' },
      { label: '销售利润', path: '/module/report/profit', permission: 'reports' },
      { label: '商品汇总', path: '/module/report/goods', permission: 'reports' },
    ],
  },
  {
    label: '运营提醒',
    icon: Operation,
    permission: 'dashboard',
    children: [
      { label: '运营提醒中心', path: '/module/operation/center', permission: 'dashboard' },
      { label: '我的工作台', path: '/module/workbench/my', permission: 'dashboard' },
    ],
  },
  {
    label: '系统设置',
    icon: Setting,
    permission: 'system',
    children: [
      { label: '平台设置', path: '/module/system/settings', permission: 'system' },
      { label: '管理员账号', path: '/module/system/admins', permission: 'system' },
      { label: '操作日志', path: '/module/system/logs', permission: 'system' },
    ],
  },
]

export const spareIcons = { Tickets, Document, Goods, MapLocation, User, Van }
