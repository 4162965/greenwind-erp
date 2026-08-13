<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Plus, Search } from '@element-plus/icons-vue'

const route = useRoute()
const names: Record<string, string> = { material: '物料管理', goods: '商品管理', order: '订单管理', customer: '客户管理', purchase: '采购管理', inventory: '库存管理', warehouse: '仓库管理', finance: '财务管理', report: '报表统计', staff: '员工管理', vehicle: '车辆管理', schedule: '日程安排', workflow: '审批管理', operation: '运营管理', system: '系统设置' }
const title = computed(() => names[String(route.params.module)] || '业务模块')
</script>

<template>
  <div class="page">
    <div class="page-heading compact"><div><p class="eyebrow">BUSINESS MODULE</p><h1>{{ title }}</h1><p>该模块路由与基础交互已接入，下一阶段补充真实数据和业务流程。</p></div><el-button type="primary" :icon="Plus">新建记录</el-button></div>
    <article class="panel table-panel"><div class="table-toolbar"><el-input placeholder="输入关键词搜索" :prefix-icon="Search" clearable /><el-select placeholder="全部状态"><el-option label="全部状态" value="" /><el-option label="正常" value="active" /></el-select><el-button>筛选</el-button></div><el-empty description="模块数据接口将在下一阶段实现" /></article>
  </div>
</template>

