<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowLeft, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { api } from '../../api/client'

type Row = Record<string, any>
const router = useRouter()
const loading = ref(false)
const keyword = ref('')
const active = ref('pending')
const rows = ref<Row[]>([])
const filteredRows = computed(() => rows.value.filter((row) => {
  if (active.value === 'all') return true
  if (active.value === 'pending') return ['待配送', '待出库', '待派单', '待派配送'].includes(row.status)
  return ['已出库', '已发布', '配送中', '已送达', '已完成'].includes(row.status)
}))

function itemSummary(row: Row) {
  return (row.items || []).map((item: Row) => `${item.product_name}${item.variant_name ? ` · ${item.variant_name}` : ''} × ${Number(item.quantity || 0)}${item.unit || ''}`).join('；')
}

async function loadRows() {
  loading.value = true
  try { rows.value = (await api.get('/inventory/outbound-orders', { params: { keyword: keyword.value.trim() } })).data.items || [] }
  catch (error: any) { ElMessage.error(error.response?.data?.detail || '配货任务加载失败') }
  finally { loading.value = false }
}

async function confirm(row: Row) {
  await ElMessageBox.confirm(`确认 ${row.order_no} 已完成配货出库？`, '确认出库', { type: 'warning' })
  try {
    await api.post(`/inventory/outbound-orders/${row.id}/confirm`)
    ElMessage.success('已确认出库，订单进入待配送')
    await loadRows()
  } catch (error: any) { ElMessage.error(error.response?.data?.detail || '确认出库失败') }
}

onMounted(loadRows)
</script>

<template>
  <div class="mobile-page" v-loading="loading">
    <section class="mobile-title compact-title"><button type="button" @click="router.back()"><el-icon><ArrowLeft /></el-icon></button><div><p>OUTBOUND</p><h1>仓库配货</h1></div><button type="button" @click="loadRows"><el-icon><Refresh /></el-icon></button></section>
    <section class="mobile-filter"><el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="出库单、项目、经办人" @keyup.enter="loadRows" @clear="loadRows" /><el-segmented v-model="active" :options="[{ label: '待配货', value: 'pending' }, { label: '配送中', value: 'active' }, { label: '全部', value: 'all' }]" /></section>
    <el-empty v-if="!filteredRows.length && !loading" description="暂无配货任务" />
    <section v-else class="mobile-task-list">
      <article v-for="row in filteredRows" :key="row.id" class="mobile-task-card">
        <div class="task-card-head"><strong>{{ row.order_no }}</strong><el-tag :type="row.status === '已出库' ? 'success' : 'warning'">{{ row.status }}</el-tag></div>
        <p>{{ row.project_name || '未指定项目' }} · {{ row.outbound_type }}</p>
        <div class="task-items">{{ itemSummary(row) || '暂无明细' }}</div>
        <p>经办人：{{ row.handler || '待安排' }}　日期：{{ row.outbound_date || '待确定' }}</p>
        <div v-if="row.status !== '已出库'" class="task-actions"><el-button type="success" @click="confirm(row)">确认配货出库</el-button></div>
      </article>
    </section>
  </div>
</template>
