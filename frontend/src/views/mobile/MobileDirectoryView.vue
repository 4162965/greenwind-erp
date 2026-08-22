<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ArrowLeft, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../api/client'

type Row = Record<string, any>
type ModuleConfig = { title: string; eyebrow: string; endpoint: string; search: string }

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const keyword = ref('')
const rows = ref<Row[]>([])

const configs: Record<string, ModuleConfig> = {
  vehicles: { title: '车辆记录', eyebrow: 'VEHICLES', endpoint: '/vehicles', search: '车牌、司机、车型' },
  projects: { title: '客户项目', eyebrow: 'PROJECTS', endpoint: '/projects', search: '项目、客户、负责人' },
  'project-plants': { title: '项目植物', eyebrow: 'PLANTS', endpoint: '/project-plants', search: '植物、规格、摆放位置' },
  orders: { title: '订单进度', eyebrow: 'ORDERS', endpoint: '/orders', search: '订单号、项目、客户' },
  reports: { title: '项目费用', eyebrow: 'REPORTS', endpoint: '/reports/project-costs', search: '项目名称' },
}

const moduleName = computed(() => String(route.params.module || 'projects'))
const config = computed(() => configs[moduleName.value] || configs.projects)
const displayRows = computed(() => {
  const term = keyword.value.trim().toLowerCase()
  if (!term || moduleName.value !== 'project-plants') return rows.value
  return rows.value.filter((row) => JSON.stringify(row).toLowerCase().includes(term))
})

function money(value: unknown) { return `¥${Number(value || 0).toFixed(2)}` }

async function loadRows() {
  loading.value = true
  try {
    const params = moduleName.value === 'project-plants' ? {} : { keyword: keyword.value.trim() }
    rows.value = (await api.get(config.value.endpoint, { params })).data.items || []
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || `${config.value.title}加载失败`)
  } finally {
    loading.value = false
  }
}

function title(row: Row) {
  if (moduleName.value === 'vehicles') return row.plate_no || '未填写车牌'
  if (moduleName.value === 'projects') return row.name || row.project_name || '未命名项目'
  if (moduleName.value === 'project-plants') return row.product_name || '未命名植物'
  if (moduleName.value === 'orders') return row.order_no || '未编号订单'
  return row.project_name || '未命名项目'
}

function subtitle(row: Row) {
  if (moduleName.value === 'vehicles') return `${row.vehicle_type || '未填写车型'} · 司机 ${row.driver_name || '待安排'}`
  if (moduleName.value === 'projects') return `${row.customer_name || '未关联客户'} · ${row.business_types || row.business_type || '未分类'}`
  if (moduleName.value === 'project-plants') return `${row.project_name || '未关联项目'} · ${row.specification || '默认规格'}`
  if (moduleName.value === 'orders') return `${row.project_name || row.customer_name || '未关联项目'} · ${row.order_type_label || row.order_type || ''}`
  return `收入 ${money(row.customer_income)} · 成本 ${money(row.total_cost)}`
}

function detail(row: Row) {
  if (moduleName.value === 'vehicles') return `状态：${row.status || '启用'}　载重：${row.capacity || '未填写'}`
  if (moduleName.value === 'projects') return `${row.address || '未填写地址'}　负责人：${row.supervisor_name || row.customer_service_name || row.manager_name || row.contact_person || '待安排'}`
  if (moduleName.value === 'project-plants') return `位置：${row.location_name || '未填写'}　数量：${Number(row.quantity || 0)} ${row.unit || '盆'}　养护员：${row.maintainer_name || '待安排'}`
  if (moduleName.value === 'orders') return `状态：${row.status || '待处理'}　日期：${row.order_date || ''}　金额：${money(row.total_amount)}`
  return `利润 ${money(row.profit)}　利润率 ${Number(row.profit_rate || 0).toFixed(1)}%　已收 ${money(row.receipt_amount)}`
}

watch(() => route.params.module, () => { keyword.value = ''; loadRows() })
onMounted(loadRows)
</script>

<template>
  <div class="mobile-page" v-loading="loading">
    <section class="mobile-title compact-title"><button type="button" @click="router.back()"><el-icon><ArrowLeft /></el-icon></button><div><p>{{ config.eyebrow }}</p><h1>{{ config.title }}</h1></div><button type="button" @click="loadRows"><el-icon><Refresh /></el-icon></button></section>
    <section class="mobile-filter"><el-input v-model="keyword" clearable :prefix-icon="Search" :placeholder="config.search" @keyup.enter="loadRows" @clear="loadRows" /></section>
    <div class="mobile-stat-line"><span>共 {{ displayRows.length }} 条</span></div>
    <el-empty v-if="!displayRows.length && !loading" :description="`暂无${config.title}数据`" />
    <section v-else class="mobile-list mobile-directory-list">
      <article v-for="row in displayRows" :key="row.id || row.project_id">
        <div class="mobile-directory-head"><strong>{{ title(row) }}</strong><el-tag v-if="row.status" size="small" :type="['已完成','启用','正常'].includes(row.status) ? 'success' : 'info'">{{ row.status }}</el-tag></div>
        <span>{{ subtitle(row) }}</span><small>{{ detail(row) }}</small>
      </article>
    </section>
  </div>
</template>

<style scoped>
.mobile-directory-list article { padding:14px; border:1px solid #e0e9e4; background:#fff; }
.mobile-directory-head { display:flex; align-items:flex-start; justify-content:space-between; gap:10px; }
.mobile-directory-head strong { min-width:0; overflow-wrap:anywhere; }
</style>
