<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, Calendar, Check, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const highlightNo = ref('')
const statusFilter = ref('pending')
const orders = ref<Row[]>([])
const products = ref<Row[]>([])
const employees = ref<Row[]>([])
const vehicles = ref<Row[]>([])
const variantCache = reactive<Record<number, Row[]>>({})
const dialogVisible = ref(false)
const scheduleVisible = ref(false)
const form = reactive<Row>({})
const scheduleForm = reactive<Row>({})
const statusTabs = [
  { label: '待配送', value: 'pending' },
  { label: '配送中', value: 'active' },
  { label: '已完成', value: 'done' },
  { label: '全部', value: 'all' },
]

const filteredOrders = computed(() => orders.value.filter((row) => {
  if (statusFilter.value === 'all') return true
  if (statusFilter.value === 'pending') return ['待配送', '待出库', '待派单', '待派配送'].includes(row.status)
  if (statusFilter.value === 'active') return ['已出库', '已发布', '配送中', '已出发', '已送达'].includes(row.status)
  if (statusFilter.value === 'done') return ['已完成'].includes(row.status)
  return true
}))

const statusCounts = computed(() => ({
  pending: orders.value.filter((row) => ['待配送', '待出库', '待派单', '待派配送'].includes(row.status)).length,
  active: orders.value.filter((row) => ['已出库', '已发布', '配送中', '已出发', '已送达'].includes(row.status)).length,
  done: orders.value.filter((row) => row.status === '已完成').length,
  all: orders.value.length,
}))

function resetForm(values: Row) {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, values)
}

function resetScheduleForm(values: Row) {
  Object.keys(scheduleForm).forEach((key) => delete scheduleForm[key])
  Object.assign(scheduleForm, values)
}

function emptyItem() {
  return { product_id: null, variant_id: null, product_name: '', variant_name: '', quantity: 1, unit: '件', unit_price: 0, notes: '' }
}

function emptyOrder() {
  return {
    order_no: `PS-${Date.now().toString().slice(-8)}`,
    outbound_type: '项目领用',
    project_name: '',
    handler: '',
    outbound_date: new Date().toISOString().slice(0, 10),
    notes: '',
    items: [emptyItem()],
  }
}

function parseJson<T>(value: string | undefined, fallback: T): T {
  if (!value) return fallback
  try { return JSON.parse(value) as T } catch { return fallback }
}

function variantLabel(item: Row) {
  const values = parseJson<Record<string, string>>(item.specification_values, {})
  return Object.values(values).filter(Boolean).join(' / ') || item.specification || item.code
}

function formatNumber(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') return ''
  const number = Number(value)
  if (Number.isNaN(number)) return ''
  return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
}

function orderTotal(row: Row) {
  return (row.items || []).reduce((sum: number, item: Row) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0)
}

function itemSummary(row: Row) {
  return (row.items || []).map((item: Row) => `${item.product_name}${item.variant_name ? ' / ' + item.variant_name : ''} × ${formatNumber(item.quantity)}${item.unit}`).join('；')
}

async function loadProducts() {
  products.value = (await api.get('/products')).data.items
}

async function loadEmployees() {
  employees.value = (await api.get('/employees')).data.items
}

async function loadVehicles() {
  vehicles.value = (await api.get('/vehicles')).data.items
}

async function loadVariants(productId: number | string | null) {
  const key = Number(productId)
  if (!key || variantCache[key]) return
  variantCache[key] = (await api.get(`/products/${key}/variants`)).data.items
}

async function loadOrders() {
  loading.value = true
  try {
    orders.value = (await api.get('/inventory/outbound-orders', { params: { keyword: keyword.value.trim() } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '出库单加载失败')
  } finally {
    loading.value = false
  }
}

function applyRouteKeyword() {
  highlightNo.value = String(route.query.highlight || '').trim()
}

function rowClassName({ row }: { row: Row }) {
  return highlightNo.value && row.order_no === highlightNo.value ? 'highlight-row' : ''
}

async function openCreate() {
  await loadProducts()
  resetForm(emptyOrder())
  dialogVisible.value = true
}

function addItem() {
  form.items.push(emptyItem())
}

function removeItem(index: number | string) {
  if (form.items.length === 1) { ElMessage.warning('至少保留一条出库明细'); return }
  form.items.splice(Number(index), 1)
}

async function handleProductChange(item: Row) {
  const product = products.value.find((entry) => entry.id === item.product_id)
  item.product_name = product?.name || ''
  item.variant_id = null
  item.variant_name = ''
  item.unit = product?.purchase_unit || product?.unit || '件'
  item.unit_price = product?.reference_purchase_price || 0
  await loadVariants(item.product_id)
}

function handleVariantChange(item: Row) {
  const variant = (variantCache[item.product_id] || []).find((entry) => entry.id === item.variant_id)
  item.variant_name = variant ? variantLabel(variant) : ''
  if (variant?.unit) item.unit = variant.unit
  item.unit_price = variant?.reference_purchase_price || item.unit_price || 0
}

function validateForm() {
  if (!form.order_no) { ElMessage.warning('请填写出库单号'); return false }
  if (!form.items?.length) { ElMessage.warning('请添加出库明细'); return false }
  if (form.items.some((item: Row) => !item.product_id || Number(item.quantity) <= 0)) {
    ElMessage.warning('请完整填写出库商品和数量')
    return false
  }
  return true
}

async function saveOrder() {
  if (!validateForm()) return
  saving.value = true
  try {
    await api.post('/inventory/outbound-orders', { ...form, outbound_date: form.outbound_date || null })
    ElMessage.success('出库单已新建')
    dialogVisible.value = false
    await loadOrders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '出库单保存失败')
  } finally {
    saving.value = false
  }
}

async function confirmOrder(row: Row) {
  await ElMessageBox.confirm(`确认出库单“${row.order_no}”正式出库吗？确认后会扣减库存并生成库存流水。`, '确认出库', { type: 'warning' })
  try {
    await api.post(`/inventory/outbound-orders/${row.id}/confirm`)
    ElMessage.success('出库完成，库存已扣减')
    await loadOrders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '确认出库失败')
  }
}

async function openSchedule(row: Row) {
  await Promise.all([loadEmployees(), loadVehicles()])
  resetScheduleForm({
    order_id: row.id,
    order_no: row.order_no,
    project_name: row.project_name,
    schedule_date: row.outbound_date || new Date().toISOString().slice(0, 10),
    driver_id: null,
    assistant_ids: [],
    vehicle_id: null,
    notes: `由出库单 ${row.order_no} 生成；经办人：${row.handler || ''}`,
  })
  scheduleVisible.value = true
}

async function createSchedule() {
  if (!scheduleForm.order_id) return
  saving.value = true
  try {
    const payload = {
      schedule_date: scheduleForm.schedule_date || null,
      driver_id: scheduleForm.driver_id || null,
      assistant_ids: (scheduleForm.assistant_ids || []).join(','),
      vehicle_id: scheduleForm.vehicle_id || null,
      notes: scheduleForm.notes || '',
    }
    const response = await api.post(`/schedules/from-outbound/${scheduleForm.order_id}`, payload)
    ElMessage.success(response.data.status === 'exists' ? `安排已存在：${response.data.task_no}` : `已生成每日安排：${response.data.task_no}`)
    scheduleVisible.value = false
    await loadOrders()
    router.push({ path: '/module/schedule/list', query: { date: scheduleForm.schedule_date || '' } })
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '生成每日安排失败')
  } finally {
    saving.value = false
  }
}

watch(() => route.query.keyword, async () => {
  applyRouteKeyword()
  await loadOrders()
})

applyRouteKeyword()
loadProducts()
loadOrders()
</script>

<template>
  <div class="page outbound-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">DELIVERY</p>
        <h1>出库单</h1>
        <p>用于项目领用、销售出库、换花出库、报损等库存扣减场景；出库单可以继续生成每日配送安排。</p>
      </div>
      <el-button type="success" :icon="Plus" @click="openCreate">新增出库单</el-button>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="搜索单号、项目/用途、经办人" @keyup.enter="loadOrders" @clear="loadOrders" />
        <el-radio-group v-model="statusFilter" class="status-tabs">
          <el-radio-button v-for="tab in statusTabs" :key="tab.value" :value="tab.value">{{ tab.label }} {{ statusCounts[tab.value as keyof typeof statusCounts] }}</el-radio-button>
        </el-radio-group>
        <el-button type="success" plain :icon="Search" @click="loadOrders">查询</el-button>
        <el-button :icon="Refresh" @click="keyword=''; loadOrders()">重置</el-button>
      </div>
      <el-table v-loading="loading" :data="filteredOrders" stripe :row-class-name="rowClassName">
        <el-table-column prop="order_no" label="出库单号" min-width="140" />
        <el-table-column prop="outbound_type" label="出库类型" width="105" />
        <el-table-column prop="project_name" label="项目/用途" min-width="150" />
        <el-table-column prop="handler" label="经办人" width="95" />
        <el-table-column prop="outbound_date" label="出库日期" width="115" />
        <el-table-column label="明细" min-width="260"><template #default="scope">{{ itemSummary(scope.row) }}</template></el-table-column>
        <el-table-column label="成本金额" width="105"><template #default="scope">¥{{ orderTotal(scope.row).toFixed(2) }}</template></el-table-column>
        <el-table-column label="状态" width="92"><template #default="scope"><el-tag :type="scope.row.status === '已出库' ? 'success' : 'warning'">{{ scope.row.status }}</el-tag></template></el-table-column>
        <el-table-column label="操作" fixed="right" width="86">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">更多<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="openSchedule(scope.row)">安排配送</el-dropdown-item>
                  <el-dropdown-item :disabled="scope.row.status === '已出库'" @click="confirmOrder(scope.row)">确认备货</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <el-dialog v-model="dialogVisible" title="新增出库单" width="92%" top="5vh" destroy-on-close>
      <el-form label-position="top" class="purchase-form">
        <section class="form-section">
          <div class="form-grid four">
            <el-form-item label="出库单号" required><el-input v-model="form.order_no" /></el-form-item>
            <el-form-item label="出库类型">
              <el-select v-model="form.outbound_type" style="width:100%">
                <el-option label="项目领用" value="项目领用" />
                <el-option label="销售出库" value="销售出库" />
                <el-option label="换花出库" value="换花出库" />
                <el-option label="赠送出库" value="赠送出库" />
                <el-option label="撤花报损" value="撤花报损" />
                <el-option label="其他出库" value="其他出库" />
              </el-select>
            </el-form-item>
            <el-form-item label="项目/用途"><el-input v-model="form.project_name" placeholder="例如：金融中心项目 / 临时销售" /></el-form-item>
            <el-form-item label="经办人"><el-input v-model="form.handler" /></el-form-item>
            <el-form-item label="出库日期"><el-date-picker v-model="form.outbound_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
            <el-form-item label="备注" class="wide"><el-input v-model="form.notes" /></el-form-item>
          </div>
        </section>

        <section class="form-section purchase-items-section">
          <div class="section-title"><strong>出库明细</strong><span>选择商品规格，确认出库时扣减库存</span><el-button link type="success" :icon="Plus" @click="addItem">添加明细</el-button></div>
          <div class="purchase-item-table outbound-item-table">
            <div class="purchase-item-row outbound-item-row purchase-item-header"><div>商品</div><div>规格/型号</div><div>数量</div><div>单位</div><div>成本价</div><div>成本小计</div><div>备注</div><div>操作</div></div>
            <div v-for="(item,index) in form.items" :key="index" class="purchase-item-row outbound-item-row">
              <div><el-select v-model="item.product_id" filterable placeholder="选择商品" @change="()=>handleProductChange(item)"><el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id" /></el-select></div>
              <div><el-select v-model="item.variant_id" filterable clearable placeholder="可选规格" @focus="loadVariants(item.product_id)" @change="()=>handleVariantChange(item)"><el-option v-for="variant in variantCache[item.product_id] || []" :key="variant.id" :label="variantLabel(variant)" :value="variant.id" /></el-select></div>
              <div><el-input-number v-model="item.quantity" :min="0.01" :controls="false" /></div>
              <div><el-input v-model="item.unit" /></div>
              <div><el-input-number v-model="item.unit_price" :min="0" :controls="false" /></div>
              <div>¥{{ (Number(item.quantity || 0) * Number(item.unit_price || 0)).toFixed(2) }}</div>
              <div><el-input v-model="item.notes" /></div>
              <div><el-button link type="danger" @click="removeItem(index)">删除</el-button></div>
            </div>
          </div>
        </section>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="success" :loading="saving" @click="saveOrder">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="scheduleVisible" title="安排配送" width="760px" destroy-on-close>
      <el-form label-position="top" class="purchase-form">
        <div class="form-grid four">
          <el-form-item label="来源出库单"><el-input v-model="scheduleForm.order_no" disabled /></el-form-item>
          <el-form-item label="项目/用途"><el-input v-model="scheduleForm.project_name" disabled /></el-form-item>
          <el-form-item label="配送日期"><el-date-picker v-model="scheduleForm.schedule_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
          <div class="dispatch-assignment-row">
            <el-form-item label="车辆">
              <el-select v-model="scheduleForm.vehicle_id" filterable clearable style="width:100%" placeholder="可不选">
                <el-option v-for="vehicle in vehicles" :key="vehicle.id" :label="vehicle.plate_no" :value="vehicle.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="司机">
              <el-select v-model="scheduleForm.driver_id" filterable clearable style="width:100%" placeholder="选择司机">
                <el-option v-for="employee in employees" :key="employee.id" :label="employee.name" :value="employee.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="跟车/配送人员">
              <el-select v-model="scheduleForm.assistant_ids" multiple filterable clearable collapse-tags style="width:100%" placeholder="可多选">
                <el-option v-for="employee in employees" :key="employee.id" :label="employee.name" :value="employee.id" />
              </el-select>
            </el-form-item>
          </div>
          <el-form-item label="备注" class="wide"><el-input v-model="scheduleForm.notes" /></el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="scheduleVisible=false">取消</el-button>
        <el-button type="success" :loading="saving" @click="createSchedule">生成待发布安排</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
:deep(.highlight-row) {
  --el-table-tr-bg-color: #ffe08a;
  color: #7a3b00;
  box-shadow: inset 6px 0 0 #d97706;
}

.dispatch-assignment-row {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.dispatch-assignment-row :deep(.el-form-item) {
  margin-bottom: 0;
}
</style>
