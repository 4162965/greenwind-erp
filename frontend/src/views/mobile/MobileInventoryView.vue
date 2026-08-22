<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ArrowLeft, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { api } from '../../api/client'

type Row = Record<string, any>

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const rows = ref<Row[]>([])
const projects = ref<Row[]>([])
const orders = ref<Row[]>([])
const adjustVisible = ref(false)
const allocateVisible = ref(false)
const selected = ref<Row>({})
const adjustForm = reactive({ new_stock: 0, reason: '' })
const allocateForm = reactive<Row>({ project_id: null, business_order_id: null, quantity: 1, notes: '' })

function numberText(value: unknown) {
  const number = Number(value || 0)
  return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
}

async function loadRows() {
  loading.value = true
  try {
    rows.value = (await api.get('/inventory', { params: { keyword: keyword.value.trim() } })).data.items || []
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '库存余量加载失败')
  } finally {
    loading.value = false
  }
}

async function loadDestinations() {
  const [projectRes, orderRes] = await Promise.all([api.get('/projects'), api.get('/orders')])
  projects.value = projectRes.data.items || []
  orders.value = orderRes.data.items || []
}

function openAdjust(row: Row) {
  selected.value = row
  adjustForm.new_stock = Number(row.available_quantity || row.stock || 0)
  adjustForm.reason = ''
  adjustVisible.value = true
}

async function saveAdjust() {
  if (!adjustForm.reason.trim()) {
    ElMessage.warning('请填写盘点差异原因')
    return
  }
  saving.value = true
  try {
    await api.post('/inventory/adjust', { receipt_item_id: selected.value.receipt_item_id, new_stock: Number(adjustForm.new_stock), notes: adjustForm.reason })
    ElMessage.success('库存余量已调整')
    adjustVisible.value = false
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '盘点调整失败')
  } finally {
    saving.value = false
  }
}

async function openAllocate(row: Row) {
  selected.value = row
  allocateForm.project_id = null
  allocateForm.business_order_id = null
  allocateForm.quantity = Math.min(1, Number(row.available_quantity || 0))
  allocateForm.notes = ''
  if (!projects.value.length) await loadDestinations()
  allocateVisible.value = true
}

function orderChanged(orderId: number | null) {
  const order = orders.value.find((item) => item.id === orderId)
  if (order?.project_id) allocateForm.project_id = order.project_id
}

async function saveAllocation() {
  if (!allocateForm.project_id && !allocateForm.business_order_id) {
    ElMessage.warning('请选择项目或订单去向')
    return
  }
  saving.value = true
  try {
    const project = projects.value.find((item) => item.id === allocateForm.project_id)
    const order = orders.value.find((item) => item.id === allocateForm.business_order_id)
    await api.post(`/inventory/receipt-items/${selected.value.receipt_item_id}/allocate`, {
      project_id: allocateForm.project_id,
      project_name: project?.name || '',
      business_order_id: allocateForm.business_order_id,
      business_order_no: order?.order_no || '',
      quantity: Number(allocateForm.quantity || 0),
      notes: allocateForm.notes || '',
    })
    ElMessage.success('收据余量已分配')
    allocateVisible.value = false
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '余量分配失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadRows)
</script>

<template>
  <div class="mobile-page" v-loading="loading">
    <section class="mobile-title compact-title">
      <button type="button" @click="router.back()"><el-icon><ArrowLeft /></el-icon></button>
      <div><p>INVENTORY</p><h1>商品库存</h1></div>
      <button type="button" @click="loadRows"><el-icon><Refresh /></el-icon></button>
    </section>
    <section class="mobile-filter"><el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="商品、规格编码、收据号" @keyup.enter="loadRows" @clear="loadRows" /></section>
    <div class="mobile-stat-line"><span>{{ rows.length }} 条未分配余量</span><span>按最早收据优先显示</span></div>
    <el-empty v-if="!rows.length && !loading" description="暂无未分配库存" />
    <section v-else class="mobile-task-list">
      <article v-for="row in rows" :key="row.receipt_item_id" class="mobile-task-card">
        <div class="task-card-head"><strong>{{ row.product_name }}</strong><el-tag type="success">{{ numberText(row.available_quantity) }} {{ row.unit }}</el-tag></div>
        <p>{{ row.variant_code || '无规格编码' }} · {{ row.specification || '默认规格' }}</p>
        <div class="task-items">收据 {{ row.receipt_no }}　{{ row.receipt_date || '' }}<br>单价 ¥{{ Number(row.unit_price || 0).toFixed(2) }}　库存金额 ¥{{ Number(row.stock_value || 0).toFixed(2) }}</div>
        <p>供应商：{{ row.supplier || '未填写' }}</p>
        <div class="task-actions"><el-button @click="openAdjust(row)">盘点调整</el-button><el-button type="success" @click="openAllocate(row)">分配去向</el-button></div>
      </article>
    </section>

    <el-dialog v-model="adjustVisible" title="库存盘点调整" width="92%">
      <p>{{ selected.product_name }} · {{ selected.specification }}</p>
      <el-form label-position="top">
        <el-form-item label="盘点后数量"><el-input-number v-model="adjustForm.new_stock" :min="0" :precision="2" :controls="false" /></el-form-item>
        <el-form-item label="差异原因" required><el-input v-model="adjustForm.reason" type="textarea" :rows="3" placeholder="损耗、退回补录、盘盈等" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="adjustVisible=false">取消</el-button><el-button type="success" :loading="saving" @click="saveAdjust">保存调整</el-button></template>
    </el-dialog>

    <el-dialog v-model="allocateVisible" title="分配项目去向" width="94%">
      <p>{{ selected.product_name }} · 可分配 {{ numberText(selected.available_quantity) }} {{ selected.unit }}</p>
      <el-form label-position="top">
        <el-form-item label="关联订单"><el-select v-model="allocateForm.business_order_id" filterable clearable placeholder="有订单时优先选择" @change="orderChanged"><el-option v-for="order in orders" :key="order.id" :label="`${order.order_no} · ${order.project_name || order.customer_name}`" :value="order.id" /></el-select></el-form-item>
        <el-form-item label="项目"><el-select v-model="allocateForm.project_id" filterable clearable placeholder="选择项目"><el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" /></el-select></el-form-item>
        <el-form-item label="分配数量" required><el-input-number v-model="allocateForm.quantity" :min="0.01" :max="Number(selected.available_quantity || 0)" :precision="2" :controls="false" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="allocateForm.notes" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="allocateVisible=false">取消</el-button><el-button type="success" :loading="saving" @click="saveAllocation">确认分配</el-button></template>
    </el-dialog>
  </div>
</template>
