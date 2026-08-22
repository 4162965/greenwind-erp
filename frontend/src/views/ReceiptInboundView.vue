<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Delete, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const route = useRoute()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const unassignedOnly = ref(true)
const receipts = ref<Row[]>([])
const products = ref<Row[]>([])
const variantCache = reactive<Record<number, Row[]>>({})
const dialogVisible = ref(false)
const form = reactive<Row>({
  receipt_no: '',
  supplier: '',
  purchaser: '',
  receipt_date: new Date().toISOString().slice(0, 10),
  source_purchase_no: '',
  notes: '',
  items: [],
})

const summary = computed(() => {
  let total = 0
  let unassigned = 0
  for (const receipt of receipts.value) {
    for (const item of receipt.items || []) {
      total += Number(item.total_quantity || 0)
      unassigned += Number(item.available_quantity || 0)
    }
  }
  return { receipts: receipts.value.length, total, unassigned }
})

function formatNumber(value: unknown) {
  const number = Number(value || 0)
  return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
}

function money(value: unknown) {
  return `¥${Number(value || 0).toFixed(2)}`
}

function variantLabel(item: Row) {
  return item.specification || item.code || item.variant_name || ''
}

async function loadProducts() {
  products.value = (await api.get('/products')).data.items || []
}

async function loadVariants(productId: number | string | null) {
  const key = Number(productId)
  if (!key || variantCache[key]) return
  variantCache[key] = (await api.get(`/products/${key}/variants`)).data.items || []
}

async function loadReceipts() {
  loading.value = true
  try {
    receipts.value = (await api.get('/purchases/receipts', {
      params: { keyword: keyword.value.trim(), unassigned_only: unassignedOnly.value },
    })).data.items || []
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '收据加载失败')
  } finally {
    loading.value = false
  }
}

function emptyItem() {
  return {
    product_id: null,
    variant_id: null,
    product_name: '',
    variant_name: '',
    quantity: 1,
    unit: '件',
    unit_price: 0,
    project_name: '',
    business_order_no: '',
    allocation_quantity: 0,
    notes: '',
  }
}

function resetForm() {
  Object.assign(form, {
    receipt_no: `RJ-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${Date.now().toString().slice(-4)}`,
    supplier: '',
    purchaser: '',
    receipt_date: new Date().toISOString().slice(0, 10),
    source_purchase_no: '',
    notes: '',
    items: [emptyItem()],
  })
}

async function openDraftFromRoute() {
  if (!route.query.draft) return
  const raw = sessionStorage.getItem('greenwind_receipt_draft')
  if (!raw) return
  let draft: Row
  try {
    draft = JSON.parse(raw)
  } catch {
    sessionStorage.removeItem('greenwind_receipt_draft')
    return
  }
  await loadProducts()
  Object.assign(form, {
    receipt_no: draft.receipt_no || `RJ-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${Date.now().toString().slice(-4)}`,
    supplier: draft.supplier || '',
    purchaser: draft.purchaser || '',
    receipt_date: draft.receipt_date || new Date().toISOString().slice(0, 10),
    source_purchase_no: draft.source_purchase_no || '',
    notes: draft.notes || '',
    items: Array.isArray(draft.items) && draft.items.length ? draft.items.map((item: Row) => ({
      ...emptyItem(),
      ...item,
      quantity: Number(item.quantity || 0),
      unit_price: Number(item.unit_price || 0),
      allocation_quantity: Number(item.allocation_quantity || 0),
    })) : [emptyItem()],
  })
  await Promise.all((form.items || []).map((item: Row) => loadVariants(item.product_id)))
  sessionStorage.removeItem('greenwind_receipt_draft')
  dialogVisible.value = true
}

async function openCreate() {
  await loadProducts()
  resetForm()
  dialogVisible.value = true
}

function addItem() {
  form.items.push(emptyItem())
}

function removeItem(index: number | string) {
  if (form.items.length <= 1) {
    ElMessage.warning('至少保留一条收据明细')
    return
  }
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
  item.unit = variant?.unit || item.unit
  if (variant?.reference_purchase_price) item.unit_price = variant.reference_purchase_price
}

function payloadItems() {
  return form.items.map((item: Row) => {
    const allocationQuantity = Number(item.allocation_quantity || 0)
    const allocations = allocationQuantity > 0 ? [{
      quantity: allocationQuantity,
      project_name: item.project_name,
      business_order_no: item.business_order_no,
      notes: item.notes,
    }] : []
    return {
      product_id: item.product_id,
      variant_id: item.variant_id,
      product_name: item.product_name,
      variant_name: item.variant_name,
      quantity: Number(item.quantity || 0),
      unit: item.unit,
      unit_price: Number(item.unit_price || 0),
      notes: item.notes,
      allocations,
    }
  })
}

function validateForm() {
  if (!form.items.length) return '请添加收据明细'
  for (const item of form.items) {
    if (!item.product_id || Number(item.quantity || 0) <= 0) return '请完整填写商品和数量'
    if (Number(item.unit_price || 0) < 0) return '单价不能小于0'
    if (Number(item.allocation_quantity || 0) > Number(item.quantity || 0)) return '去向数量不能超过收据数量'
  }
  return ''
}

async function saveReceipt() {
  const message = validateForm()
  if (message) {
    ElMessage.warning(message)
    return
  }
  saving.value = true
  try {
    await api.post('/purchases/receipts', {
      receipt_no: form.receipt_no,
      supplier: form.supplier,
      purchaser: form.purchaser,
      receipt_date: form.receipt_date || null,
      source_purchase_no: form.source_purchase_no,
      notes: form.notes,
      items: payloadItems(),
    })
    ElMessage.success('收据入库成功')
    dialogVisible.value = false
    await loadReceipts()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '收据入库失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await loadReceipts()
  await openDraftFromRoute()
})
</script>

<template>
  <div class="page purchase-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">RECEIPT INBOUND</p>
        <h1>收据入库</h1>
        <p>按采购收据录入货品、单价和项目去向，未安排数量会进入库存余量。</p>
      </div>
      <el-button type="success" :icon="Plus" @click="openCreate">新增收据</el-button>
    </div>

    <div class="inventory-summary">
      <div><span>收据数量</span><strong>{{ summary.receipts }}</strong></div>
      <div><span>收据总数量</span><strong>{{ formatNumber(summary.total) }}</strong></div>
      <div><span>未安排余量</span><strong>{{ formatNumber(summary.unassigned) }}</strong></div>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar inventory-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="搜索收据、供应商、商品或规格" @keyup.enter="loadReceipts" @clear="loadReceipts" />
        <el-checkbox v-model="unassignedOnly" @change="loadReceipts">只看有未安排余量</el-checkbox>
        <el-button type="success" plain :icon="Search" @click="loadReceipts">查询</el-button>
        <el-button :icon="Refresh" @click="keyword=''; unassignedOnly=true; loadReceipts()">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="receipts" stripe row-key="id">
        <el-table-column type="expand">
          <template #default="scope">
            <el-table :data="scope.row.items || []" size="small" border>
              <el-table-column prop="product_name" label="商品" min-width="160" />
              <el-table-column prop="variant_name" label="规格" min-width="120" />
              <el-table-column label="收据数量" width="110"><template #default="item">{{ formatNumber(item.row.total_quantity) }} {{ item.row.unit }}</template></el-table-column>
              <el-table-column label="未安排" width="110"><template #default="item"><el-tag type="success">{{ formatNumber(item.row.available_quantity) }} {{ item.row.unit }}</el-tag></template></el-table-column>
              <el-table-column label="单价" width="100"><template #default="item">{{ money(item.row.unit_price) }}</template></el-table-column>
              <el-table-column label="合计" width="110"><template #default="item">{{ money(item.row.total_amount) }}</template></el-table-column>
            </el-table>
          </template>
        </el-table-column>
        <el-table-column prop="receipt_no" label="收据号" min-width="150" />
        <el-table-column prop="supplier" label="供应商" min-width="130" />
        <el-table-column prop="purchaser" label="采购/仓管" width="115" />
        <el-table-column prop="receipt_date" label="收据日期" width="120" />
        <el-table-column prop="source_purchase_no" label="关联采购单" min-width="140" />
        <el-table-column label="状态" width="105"><template #default="scope"><el-tag :type="scope.row.status === '有未安排' ? 'success' : 'info'">{{ scope.row.status }}</el-tag></template></el-table-column>
        <el-table-column prop="notes" label="备注" min-width="180" show-overflow-tooltip />
      </el-table>
    </article>

    <el-dialog v-model="dialogVisible" title="新增收据入库" width="94%" top="5vh" destroy-on-close>
      <el-form label-position="top" class="purchase-form">
        <div class="form-grid four">
          <el-form-item label="收据号"><el-input v-model="form.receipt_no" /></el-form-item>
          <el-form-item label="供应商"><el-input v-model="form.supplier" /></el-form-item>
          <el-form-item label="采购/仓管"><el-input v-model="form.purchaser" /></el-form-item>
          <el-form-item label="收据日期"><el-date-picker v-model="form.receipt_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
          <el-form-item label="关联采购单"><el-input v-model="form.source_purchase_no" /></el-form-item>
          <el-form-item label="备注" class="wide"><el-input v-model="form.notes" type="textarea" :rows="2" /></el-form-item>
        </div>

        <section class="form-section purchase-items-section">
          <div class="section-title"><strong>收据货品和去向</strong><span>去向数量不填或小于收据数量时，剩余部分进入未安排库存</span><el-button link type="success" :icon="Plus" @click="addItem">添加货品</el-button></div>
          <div class="purchase-item-table receipt-item-table">
            <div class="receipt-item-row purchase-item-header"><div>商品</div><div>规格</div><div>数量</div><div>单位</div><div>单价</div><div>去向项目</div><div>订单号</div><div>去向数量</div><div>备注</div><div>操作</div></div>
            <div v-for="(item,index) in form.items" :key="index" class="receipt-item-row">
              <div><el-select v-model="item.product_id" filterable placeholder="商品" @change="handleProductChange(item)"><el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id" /></el-select></div>
              <div><el-select v-model="item.variant_id" clearable filterable placeholder="规格" @visible-change="loadVariants(item.product_id)" @change="handleVariantChange(item)"><el-option v-for="variant in (variantCache[item.product_id] || [])" :key="variant.id" :label="variantLabel(variant)" :value="variant.id" /></el-select></div>
              <div><el-input-number v-model="item.quantity" :min="0" :precision="2" :controls="false" /></div>
              <div><el-input v-model="item.unit" /></div>
              <div><el-input-number v-model="item.unit_price" :min="0" :precision="2" :controls="false" /></div>
              <div><el-input v-model="item.project_name" placeholder="可空" /></div>
              <div><el-input v-model="item.business_order_no" placeholder="可空" /></div>
              <div><el-input-number v-model="item.allocation_quantity" :min="0" :max="Number(item.quantity || 0)" :precision="2" :controls="false" /></div>
              <div><el-input v-model="item.notes" /></div>
              <div><el-button link type="danger" :icon="Delete" @click="removeItem(index)" /></div>
            </div>
          </div>
        </section>
      </el-form>
      <template #footer>
        <div class="editor-footer"><el-button @click="dialogVisible=false">取消</el-button><el-button type="success" :loading="saving" @click="saveReceipt">保存收据</el-button></div>
      </template>
    </el-dialog>
  </div>
</template>
