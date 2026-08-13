<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Search } from '@element-plus/icons-vue'

const route = useRoute()

const moduleNames: Record<string, string> = {
  customer: '客户管理',
  customers: '客户管理',
  projects: '项目管理',
  staff: '员工管理',
  purchase: '采购管理',
  inventory: '仓管管理',
  vehicle: '车辆管理',
  workflow: '审批管理',
  finance: '财务管理',
  report: '报表统计',
  operation: '运营资料',
  system: '系统管理',
}

const title = computed(() => {
  const metaTitle = route.meta.title
  if (typeof metaTitle === 'string') return metaTitle
  return moduleNames[String(route.params.module || '')] || '功能模块'
})
</script>

<template>
  <div class="page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">BUSINESS MODULE</p>
        <h1>{{ title }}</h1>
        <p>这个模块正在整理中，先保证系统可以正常启动和测试核心流程。</p>
      </div>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar">
        <el-input placeholder="输入关键词搜索" :prefix-icon="Search" clearable />
        <el-button>查询</el-button>
      </div>
      <el-empty description="该功能正在恢复，后续会继续补全真实业务页面。" />
    </article>
  </div>
</template>
