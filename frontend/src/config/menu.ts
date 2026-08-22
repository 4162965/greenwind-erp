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
  { label: '首页工作台', value: 'dashboard' },
  { label: '商品管理', value: 'goods' },
  { label: '客户管理', value: 'customers' },
  { label: '项目管理', value: 'projects' },
  { label: '订单管理', value: 'orders' },
  { label: '采购仓管', value: 'purchase_inventory' },
  { label: '配送养护', value: 'schedule_workflow' },
  { label: '合同财务', value: 'finance' },
  { label: '报表分析', value: 'reports' },
  { label: '员工管理', value: 'staff' },
  { label: '车辆管理', value: 'vehicle' },
  { label: '系统设置', value: 'system' },
]

export const menuItems: MenuItem[] = [
  { label: '首页工作台', path: '/', icon: House, permission: 'dashboard' },
  { label: '商品管理', path: '/goods', icon: Goods, permission: 'goods' },
  { label: '客户管理', path: '/customers', icon: User, permission: 'customers' },
  {
    label: '租摆业务',
    icon: ShoppingCart,
    permission: 'orders',
    children: [
      { label: '租摆项目管理', path: '/projects', permission: 'projects' },
      { label: '租摆订单', path: '/module/order/lease', permission: 'orders' },
      { label: '换花订单', path: '/module/order/exchange', permission: 'orders' },
      { label: '撤花订单', path: '/module/order/withdraw', permission: 'orders' },
      { label: '养护任务', path: '/module/maintenance/manage', permission: 'schedule_workflow' },
    ],
  },
  {
    label: '工程绿化',
    icon: MapLocation,
    permission: 'orders',
    children: [
      { label: '工程项目管理', path: '/projects?business=工程绿化', permission: 'projects' },
      { label: '工程订单', path: '/module/order/engineering', permission: 'orders' },
      { label: '修剪/补种任务', path: '/module/order/engineering-service', permission: 'orders' },
      { label: '物料任务', path: '/module/order/engineering-material', permission: 'orders' },
    ],
  },
  {
    label: '电网业务',
    icon: OfficeBuilding,
    permission: 'orders',
    children: [
      { label: '电网项目管理', path: '/projects?business=电网', permission: 'projects' },
      { label: '电网绿风订单', path: '/module/order/grid-greenwind', permission: 'orders' },
      { label: '电网盛景订单', path: '/module/order/grid-shengjing', permission: 'orders' },
      { label: '电网价格管理', path: '/goods?scope=grid', permission: 'goods' },
    ],
  },
  {
    label: '保洁业务',
    icon: Operation,
    permission: 'orders',
    children: [
      { label: '保洁项目管理', path: '/projects?business=保洁', permission: 'projects' },
      { label: '保洁订单', path: '/module/order/cleaning', permission: 'orders' },
      { label: '保洁任务', path: '/module/order/cleaning-service', permission: 'orders' },
      { label: '物料配送', path: '/module/order/cleaning-material', permission: 'orders' },
    ],
  },
  {
    label: '采购管理',
    icon: Briefcase,
    permission: 'purchase_inventory',
    children: [
      { label: '采购需求', path: '/module/purchase/list', permission: 'purchase_inventory' },
      { label: '我的采购任务', path: '/module/purchase/my', permission: 'purchase_inventory' },
      { label: '收据入库', path: '/module/purchase/receipts', permission: 'purchase_inventory' },
      { label: '待分配采购余量', path: '/module/inventory/check', permission: 'purchase_inventory' },
    ],
  },
  {
    label: '仓库管理',
    icon: Goods,
    permission: 'purchase_inventory',
    children: [
      { label: '库存余量与盘点', path: '/module/inventory/check', permission: 'purchase_inventory' },
      { label: '出库记录', path: '/module/warehouse/outbound', permission: 'purchase_inventory' },
    ],
  },
  {
    label: '配送管理',
    icon: Van,
    permission: 'schedule_workflow',
    children: [
      { label: '配送派单', path: '/module/schedule/list', permission: 'schedule_workflow' },
      { label: '每日安排表', path: '/module/schedule/daily', permission: 'schedule_workflow' },
    ],
  },
  {
    label: '合同财务',
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
    label: '员工车辆',
    icon: Calendar,
    children: [
      { label: '员工资料', path: '/staff', permission: 'staff' },
      { label: '车辆管理', path: '/module/vehicle/list', permission: 'vehicle' },
    ],
  },
  {
    label: '报表分析',
    icon: DataAnalysis,
    permission: 'reports',
    children: [
      { label: '项目成本', path: '/module/report/project-cost', permission: 'reports' },
      { label: '订单销售', path: '/module/report/orders', permission: 'reports' },
      { label: '销售利润', path: '/module/report/profit', permission: 'reports' },
      { label: '商品汇总', path: '/module/report/goods', permission: 'reports' },
    ],
  },
  {
    label: '系统设置',
    icon: Setting,
    permission: 'system',
    children: [
      { label: '平台设置', path: '/module/system/settings', permission: 'system' },
      { label: '管理员账号', path: '/module/system/admins', permission: 'system' },
      { label: '资料附件', path: '/module/operation/attachments', permission: 'dashboard' },
      { label: '操作日志', path: '/module/system/logs', permission: 'system' },
    ],
  },
]

export const spareIcons = { Tickets, Document, Goods, MapLocation, User, Van }
