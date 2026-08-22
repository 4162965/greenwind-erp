<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, Check, Edit, Plus, Refresh, Search, Upload } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const highlightNo = ref('')
const orders = ref<Row[]>([])
const products = ref<Row[]>([])
const employees = ref<Row[]>([])
const variantCache = reactive<Record<number, Row[]>>({})
const dialogVisible = ref(false)
const completeVisible = ref(false)
const editingId = ref<number | null>(null)

const form = reactive<Row>({})
const completeForm = reactive<Row>({})
const receiptInput = ref<HTMLInputElement>()
const receipts = ref<Row[]>([])

function resetForm(values: Row) {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, values)
}

function emptyOrder() {
  return {
    order_no: `CG-${Date.now().toString().slice(-8)}`,
    supplier: '',
    purchaser: defaultPurchaser(),
    purchase_date: new Date().toISOString().slice(0, 10),
    delivery_method: '入库',
    freight_fee: 0,
    hll_fee: 0,
    status: '待采购',
    notes: '',
    items: [emptyItem()],
  }
}

function emptyItem() {
  return { product_id: null, variant_id: null, product_name: '', variant_name: '', quantity: 1, received_quantity: 0, unit: '件', unit_price: 0, notes: '' }
}

function parseJson<T>(value: string | undefined, fallback: T): T {
  if (!value) return fallback
  try { return JSON.parse(value) as T } catch { return fallback }
}

function variantLabel(item: Row) {
  const values = parseJson<Record<string, string>>(item.specification_values, {})
  return Object.values(values).filter(Boolean).join(' · ') || item.specification || item.code
}

function orderTotal(row: Row) {
  const itemTotal = (row.items || []).reduce((sum: number, item: Row) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0)
  return itemTotal + Number(row.freight_fee || 0) + Number(row.hll_fee || 0)
}

function itemSummary(row: Row) {
  return (row.items || []).map((item: Row) => `${item.product_name}${item.variant_name ? ' · ' + item.variant_name : ''} × ${item.quantity}${item.unit}`).join('；')
}

async function loadProducts() {
  products.value = (await api.get('/products')).data.items
}

async function loadEmployees() {
  employees.value = (await api.get('/employees')).data.items
}

function defaultPurchaser() {
  const employee = employees.value.find((item) => `${item.position},${item.department},${item.name},${item.responsibility}`.includes('采购'))
  return employee?.name || ''
}

async function loadVariants(productId: number | string | null) {
  const key = Number(productId)
  if (!key || variantCache[key]) return
  variantCache[key] = (await api.get(`/products/${key}/variants`)).data.items
}

async function loadOrders() {
  loading.value = true
  try {
    orders.value = (await api.get('/purchases', { params: { keyword: keyword.value.trim() } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '采购单加载失败')
  } finally {
    loading.value = false
  }
}

async function openCreate() {
  editingId.value = null
  await Promise.all([loadProducts(), loadEmployees()])
  resetForm(emptyOrder())
  dialogVisible.value = true
}

async function openEdit(row: Row) {
  editingId.value = row.id
  await Promise.all([loadProducts(), loadEmployees()])
  await Promise.all((row.items || []).map((item: Row) => loadVariants(item.product_id)))
  resetForm({ ...row, purchase_date: row.purchase_date || '', items: (row.items || []).map((item: Row) => ({ ...item })) })
  dialogVisible.value = true
}

function resetCompleteForm(row: Row) {
  Object.keys(completeForm).forEach((key) => delete completeForm[key])
  Object.assign(completeForm, {
    ...row,
    purchase_date: row.purchase_date || '',
    items: (row.items || []).map((item: Row) => ({ ...item })),
  })
  receipts.value = []
}

function openComplete(row: Row) {
  resetCompleteForm(row)
  completeVisible.value = true
}

function uploadFile(event: Event, bucket: Row[], inputRef: HTMLInputElement | undefined, label: string) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (file.size > 8 * 1024 * 1024) {
    ElMessage.warning(`单个${label}不能超过8MB`)
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    bucket.push({ file_name: file.name, file_type: file.type || 'image/*', file_size: file.size, data_url: String(reader.result), notes: label })
    if (inputRef) inputRef.value = ''
  }
  reader.readAsDataURL(file)
}

function chooseReceipt() { receiptInput.value?.click() }
function handleReceipt(event: Event) { uploadFile(event, receipts.value, receiptInput.value, '采购收据') }
function removeReceipt(index: number) { receipts.value.splice(index, 1) }

function validateCompleteForm() {
  if (completeForm.items?.some((item: Row) => Number(item.unit_price || 0) <= 0)) {
    ElMessage.warning('请填写每个采购物品的实际采购单价')
    return false
  }
  if (!receipts.value.length) {
    ElMessage.warning('请上传采购收据')
    return false
  }
  return true
}

async function markPurchased() {
  if (!completeForm.id || !validateCompleteForm()) return
  try {
    await api.post(`/purchases/${completeForm.id}/mark-purchased`, {
      supplier: completeForm.supplier,
      freight_fee: completeForm.freight_fee,
      hll_fee: completeForm.hll_fee,
      notes: completeForm.notes,
      items: completeForm.items,
      receipts: receipts.value,
    })
    ElMessage.success('已填写采购价并上传收据，等待入库')
    completeVisible.value = false
    await loadOrders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '标记采购完成失败')
  }
}

function addItem() {
  form.items.push(emptyItem())
}

function removeItem(index: number | string) {
  if (form.items.length === 1) { ElMessage.warning('至少保留一条采购明细'); return }
  form.items.splice(Number(index), 1)
}

async function handleProductChange(item: Row) {
  const product = products.value.find((entry) => entry.id === item.product_id)
  item.product_name = product?.name || ''
  item.variant_id = null
  item.variant_name = ''
  item.unit = product?.purchase_unit || product?.unit || '件'
  await loadVariants(item.product_id)
}

function handleVariantChange(item: Row) {
  const variant = (variantCache[item.product_id] || []).find((entry) => entry.id === item.variant_id)
  item.variant_name = variant ? variantLabel(variant) : ''
  if (variant?.unit) item.unit = variant.unit
  if (variant?.reference_purchase_price) item.unit_price = variant.reference_purchase_price
}

function validateForm() {
  if (!form.order_no) { ElMessage.warning('请填写采购单号'); return false }
  if (!form.items?.length) { ElMessage.warning('请添加采购明细'); return false }
  if (form.items.some((item: Row) => !item.product_id || Number(item.quantity) <= 0)) {
    ElMessage.warning('请完整填写采购商品和数量')
    return false
  }
  return true
}

async function saveOrder() {
  if (!validateForm()) return
  saving.value = true
  try {
    const payload = { ...form, purchase_date: form.purchase_date || null }
    if (editingId.value) await api.put(`/purchases/${editingId.value}`, payload)
    else await api.post('/purchases', payload)
    ElMessage.success(`采购单${editingId.value ? '修改' : '新增'}成功`)
    dialogVisible.value = false
    await loadOrders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '采购单保存失败')
  } finally {
    saving.value = false
  }
}

async function receiveOrder(row: Row) {
  await ElMessageBox.confirm(`确认采购单“${row.order_no}”已入库吗？确认后会更新商品库存和最近采购价。`, '确认入库', { type: 'warning' })
  try {
    await api.post(`/purchases/${row.id}/receive`)
    ElMessage.success('入库完成，库存已更新')
    await loadOrders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '入库失败')
  }
}

function openReceiptInbound(row: Row) {
  const draft = {
    receipt_no: `RJ-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${Date.now().toString().slice(-4)}`,
    supplier: row.supplier || '',
    purchaser: row.purchaser || defaultPurchaser(),
    receipt_date: new Date().toISOString().slice(0, 10),
    source_purchase_no: row.order_no || '',
    notes: row.notes || '',
    items: (row.items || []).map((item: Row) => ({
      product_id: item.product_id,
      variant_id: item.variant_id,
      product_name: item.product_name,
      variant_name: item.variant_name,
      quantity: Number(item.received_quantity || item.quantity || 0),
      unit: item.unit || '件',
      unit_price: Number(item.unit_price || 0),
      project_name: '',
      business_order_no: row.source_no || '',
      allocation_quantity: 0,
      notes: item.notes || '',
    })),
  }
  sessionStorage.setItem('greenwind_receipt_draft', JSON.stringify(draft))
  router.push({ path: '/module/purchase/receipts', query: { draft: 'purchase' } })
}

function applyRouteKeyword() {
  highlightNo.value = String(route.query.highlight || '').trim()
}

function rowClassName({ row }: { row: Row }) {
  return highlightNo.value && row.order_no === highlightNo.value ? 'highlight-row' : ''
}

watch(() => route.query.keyword, async () => {
  applyRouteKeyword()
  await loadOrders()
})

applyRouteKeyword()
loadProducts()
loadEmployees()
loadOrders()
</script>

<template>
  <div class="page purchase-page">
    <div class="page-heading compact">
      <div><p class="eyebrow">PURCHASE</p><h1>采购单</h1><p>记录采购商品、实际价格、运费和入库状态，确认入库后自动更新库存。</p></div>
      <el-button type="success" :icon="Plus" @click="openCreate">新增采购单</el-button>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="搜索单号、供应商或采购员" @keyup.enter="loadOrders" @clear="loadOrders" />
        <el-button type="success" plain :icon="Search" @click="loadOrders">查询</el-button>
        <el-button :icon="Refresh" @click="keyword=''; loadOrders()">重置</el-button>
      </div>
      <el-table v-loading="loading" :data="orders" stripe :row-class-name="rowClassName">
        <el-table-column label="来源" min-width="145">
          <template #default="scope">
            <div class="source-cell">
              <el-tag size="small" :type="scope.row.source_type === '订单生成' ? 'primary' : 'info'">{{ scope.row.source_type || '采购新增' }}</el-tag>
              <span v-if="scope.row.source_no">{{ scope.row.source_no }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_by" label="新增/报单人" width="110" />
        <el-table-column prop="order_no" label="采购单号" min-width="140" />
        <el-table-column prop="supplier" label="供应商" min-width="130" />
        <el-table-column prop="purchaser" label="采购员" width="110" />
        <el-table-column prop="purchase_date" label="采购日期" width="115" />
        <el-table-column label="明细" min-width="220"><template #default="scope"><span>{{ itemSummary(scope.row) }}</span></template></el-table-column>
        <el-table-column label="合计" width="110"><template #default="scope">¥{{ orderTotal(scope.row).toFixed(2) }}</template></el-table-column>
        <el-table-column prop="delivery_method" label="处理方式" width="90" />
        <el-table-column label="状态" width="95"><template #default="scope"><el-tag :type="scope.row.status === '已入库' ? 'success' : scope.row.status === '待采购' ? 'primary' : 'warning'">{{ scope.row.status }}</el-tag></template></el-table-column>
        <el-table-column label="操作" fixed="right" width="86">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">更多<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :disabled="scope.row.status === '已入库'" @click="openEdit(scope.row)">编辑</el-dropdown-item>
                  <el-dropdown-item :disabled="['待入库','已入库'].includes(scope.row.status)" @click="openComplete(scope.row)">采购完成</el-dropdown-item>
                  <el-dropdown-item :disabled="scope.row.status === '待采购'" @click="openReceiptInbound(scope.row)">按收据入库</el-dropdown-item>
                  <el-dropdown-item :disabled="scope.row.status !== '待入库'" @click="receiveOrder(scope.row)">确认入库</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <el-dialog v-model="dialogVisible" :title="`${editingId ? '编辑' : '新增'}采购单`" width="92%" top="5vh" destroy-on-close>
      <el-form label-position="top" class="purchase-form">
        <section class="form-section">
          <div class="form-grid four">
            <el-form-item label="采购单号" required><el-input v-model="form.order_no" /></el-form-item>
            <el-form-item label="供应商"><el-input v-model="form.supplier" /></el-form-item>
            <el-form-item label="采购员">
              <el-input v-model="form.purchaser" placeholder="系统自动接单" />
              <div class="field-help">公司只有一位采购，系统会自动指定采购岗位员工</div>
            </el-form-item>
            <el-form-item label="采购日期"><el-date-picker v-model="form.purchase_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
            <el-form-item label="处理方式"><el-select v-model="form.delivery_method" style="width:100%"><el-option label="入库" value="入库" /><el-option label="供应商直送" value="供应商直送" /><el-option label="货拉拉直送" value="货拉拉直送" /></el-select></el-form-item>
            <el-form-item label="运费"><el-input-number v-model="form.freight_fee" :min="0" :controls="false" /></el-form-item>
            <el-form-item label="货拉拉费用"><el-input-number v-model="form.hll_fee" :min="0" :controls="false" /></el-form-item>
            <el-form-item label="备注"><el-input v-model="form.notes" /></el-form-item>
          </div>
        </section>

        <section class="form-section purchase-items-section">
          <div class="section-title"><strong>采购明细</strong><span>填写实际采购商品、规格、数量和单价</span><el-button link type="success" :icon="Plus" @click="addItem">添加明细</el-button></div>
          <div class="purchase-item-table">
            <div class="purchase-item-row purchase-item-header"><div>商品</div><div>规格/型号</div><div>数量</div><div>单位</div><div>单价</div><div>小计</div><div>备注</div><div>操作</div></div>
            <div v-for="(item,index) in form.items" :key="index" class="purchase-item-row">
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
      <template #footer><div class="editor-footer"><el-button @click="dialogVisible=false">取消</el-button><el-button type="success" :loading="saving" @click="saveOrder">保存采购单</el-button></div></template>
    </el-dialog>

    <el-dialog v-model="completeVisible" title="采购完成" width="900px" top="6vh" destroy-on-close>
      <el-form label-position="top" class="purchase-form">
        <section class="form-section">
          <div class="form-grid four">
            <el-form-item label="采购单号"><el-input v-model="completeForm.order_no" disabled /></el-form-item>
            <el-form-item label="供应商"><el-input v-model="completeForm.supplier" placeholder="填写供应商" /></el-form-item>
            <el-form-item label="运费"><el-input-number v-model="completeForm.freight_fee" :min="0" :controls="false" /></el-form-item>
            <el-form-item label="货拉拉费用"><el-input-number v-model="completeForm.hll_fee" :min="0" :controls="false" /></el-form-item>
            <el-form-item label="备注" class="wide"><el-input v-model="completeForm.notes" /></el-form-item>
          </div>
        </section>
        <section class="form-section purchase-items-section">
          <div class="section-title"><strong>实际采购价格</strong><span>采购完成前必须填写每个采购物品的实际采购单价</span></div>
          <div class="purchase-item-table">
            <div class="purchase-item-row purchase-item-header"><div>商品</div><div>规格/型号</div><div>数量</div><div>单位</div><div>实际采购单价</div><div>小计</div><div>备注</div><div></div></div>
            <div v-for="(item,index) in completeForm.items" :key="item.id || index" class="purchase-item-row">
              <div>{{ item.product_name }}</div>
              <div>{{ item.variant_name || '—' }}</div>
              <div><el-input-number v-model="item.quantity" :min="0.01" :controls="false" /></div>
              <div><el-input v-model="item.unit" /></div>
              <div><el-input-number v-model="item.unit_price" :min="0" :controls="false" /></div>
              <div>¥{{ (Number(item.quantity || 0) * Number(item.unit_price || 0)).toFixed(2) }}</div>
              <div><el-input v-model="item.notes" /></div>
              <div></div>
            </div>
          </div>
        </section>
        <section class="form-section">
          <div class="section-title"><strong>采购收据</strong><span>支持图片或 PDF，采购完成前必须上传</span></div>
          <input ref="receiptInput" type="file" accept="image/*,.pdf" class="hidden-input" @change="handleReceipt" />
          <div class="receipt-upload-line">
            <el-button type="primary" plain :icon="Upload" @click="chooseReceipt">上传收据</el-button>
            <span v-if="!receipts.length" class="muted">请上传采购收据照片或 PDF</span>
            <el-tag v-for="(file,index) in receipts" :key="index" closable @close="removeReceipt(index)">{{ file.file_name }}</el-tag>
          </div>
        </section>
      </el-form>
      <template #footer>
        <el-button @click="completeVisible=false">取消</el-button>
        <el-button type="success" :loading="saving" @click="markPurchased">确认采购完成</el-button>
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
</style>
