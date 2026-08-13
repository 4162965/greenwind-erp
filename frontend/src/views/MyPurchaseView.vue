<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ArrowDown, Check, Edit, Refresh, Search, Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const includeDone = ref(false)
const orders = ref<Row[]>([])
const products = ref<Row[]>([])
const variantCache = reactive<Record<number, Row[]>>({})
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<Row>({})
const receiptInput = ref<HTMLInputElement>()
const detailInput = ref<HTMLInputElement>()
const receipts = ref<Row[]>([])
const productDetails = ref<Row[]>([])

const activeCount = computed(() => orders.value.filter((row) => row.status !== '宸插叆搴?).length)
const doneCount = computed(() => orders.value.filter((row) => row.status === '宸插叆搴?).length)

function resetForm(values: Row) {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, values)
}

function parseJson<T>(value: string | undefined, fallback: T): T {
  if (!value) return fallback
  try { return JSON.parse(value) as T } catch { return fallback }
}

function variantLabel(item: Row) {
  const values = parseJson<Record<string, string>>(item.specification_values, {})
  return Object.values(values).filter(Boolean).join(' 路 ') || item.specification || item.code
}

function formatNumber(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') return ''
  const number = Number(value)
  if (Number.isNaN(number)) return ''
  return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
}

function orderTotal(row: Row) {
  const itemTotal = (row.items || []).reduce((sum: number, item: Row) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0)
  return itemTotal + Number(row.freight_fee || 0) + Number(row.hll_fee || 0)
}

function itemSummary(row: Row) {
  return (row.items || []).map((item: Row) => `${item.product_name}${item.variant_name ? ' 路 ' + item.variant_name : ''} 脳 ${formatNumber(item.quantity)}${item.unit}`).join('锛?)
}

function statusTag(status: string) {
  if (status === '宸插叆搴?) return 'success'
  if (status === '寰呭叆搴?) return 'warning'
  if (status === '寰呴噰璐?) return 'primary'
  return 'info'
}

async function loadProducts() {
  products.value = (await api.get('/products')).data.items
}

async function loadVariants(productId: number | string | null) {
  const key = Number(productId)
  if (!key || variantCache[key]) return
  variantCache[key] = (await api.get(`/products/${key}/variants`)).data.items
}

async function loadOrders() {
  loading.value = true
  try {
    orders.value = (await api.get('/purchases/my', { params: { keyword: keyword.value.trim(), include_done: includeDone.value } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鎴戠殑閲囪喘浠诲姟鍔犺浇澶辫触')
  } finally {
    loading.value = false
  }
}

async function openEdit(row: Row) {
  editingId.value = row.id
  await loadProducts()
  await Promise.all((row.items || []).map((item: Row) => loadVariants(item.product_id)))
  receipts.value = []
  productDetails.value = []
  resetForm({ ...row, purchase_date: row.purchase_date || '', items: (row.items || []).map((item: Row) => ({ ...item })) })
  dialogVisible.value = true
}

function handleVariantChange(item: Row) {
  const variant = (variantCache[item.product_id] || []).find((entry) => entry.id === item.variant_id)
  item.variant_name = variant ? variantLabel(variant) : item.variant_name
  if (variant?.unit) item.unit = variant.unit
}

function validateForm() {
  if (form.items?.some((item: Row) => Number(item.unit_price || 0) <= 0)) {
    ElMessage.warning('璇峰～鍐欐瘡涓槑缁嗙殑瀹為檯閲囪喘鍗曚环')
    return false
  }
  return true
}

function uploadFile(event: Event, bucket: Row[], inputRef: HTMLInputElement | undefined, label: string) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (file.size > 8 * 1024 * 1024) {
    ElMessage.warning(`鍗曚釜${label}涓嶈兘瓒呰繃8MB`)
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
function chooseDetail() { detailInput.value?.click() }
function handleReceipt(event: Event) { uploadFile(event, receipts.value, receiptInput.value, '閲囪喘鏀舵嵁') }
function handleDetail(event: Event) { uploadFile(event, productDetails.value, detailInput.value, '鍟嗗搧璇︽儏') }
function removeReceipt(index: number) { receipts.value.splice(index, 1) }
function removeDetail(index: number) { productDetails.value.splice(index, 1) }

async function saveOrder() {
  if (!editingId.value || !validateForm()) return
  saving.value = true
  try {
    await api.put(`/purchases/${editingId.value}`, { ...form, purchase_date: form.purchase_date || null })
    ElMessage.success('閲囪喘淇℃伅宸蹭繚瀛?)
    dialogVisible.value = false
    await loadOrders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '閲囪喘淇℃伅淇濆瓨澶辫触')
  } finally {
    saving.value = false
  }
}

async function markPurchased() {
  if (!editingId.value || !validateForm()) return
  if (!receipts.value.length) { ElMessage.warning('璇蜂笂浼犻噰璐敹鎹?); return }
  if (!productDetails.value.length) { ElMessage.warning('璇蜂笂浼犲晢鍝佽鎯?); return }
  saving.value = true
  try {
    await api.post(`/purchases/${editingId.value}/mark-purchased`, {
      supplier: form.supplier,
      freight_fee: form.freight_fee,
      hll_fee: form.hll_fee,
      notes: form.notes,
      items: form.items,
      receipts: receipts.value,
      product_details: productDetails.value,
    })
    ElMessage.success('宸蹭繚瀛橀噰璐环鍜岄檮浠讹紝閲囪喘瀹屾垚锛岀瓑寰呬粨绠″叆搴?)
    dialogVisible.value = false
    await loadOrders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鏍囪閲囪喘瀹屾垚澶辫触')
  } finally {
    saving.value = false
  }
}

loadProducts()
loadOrders()
</script>

<template>
  <div class="page my-purchase-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">MY PURCHASE</p>
        <h1>鎴戠殑閲囪喘浠诲姟</h1>
        <p>閲囪喘鍛樺伐鎺ユ敹閲囪喘鍗曪紝濉啓瀹為檯閲囪喘浠枫€佷笂浼犳敹鎹拰鍟嗗搧璇︽儏锛屽畬鎴愬悗浜ょ粰浠撶鍏ュ簱銆?/p>
      </div>
    </div>

    <div class="inventory-summary">
      <div><span>鎴戠殑閲囪喘鍗?/span><strong>{{ orders.length }}</strong></div>
      <div><span>寰呭鐞?/span><strong>{{ activeCount }}</strong></div>
      <div><span>宸插叆搴?/span><strong>{{ doneCount }}</strong></div>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="鎼滅储閲囪喘鍗曞彿銆佷緵搴斿晢" @keyup.enter="loadOrders" @clear="loadOrders" />
        <el-checkbox v-model="includeDone" @change="loadOrders">鏄剧ず宸插叆搴?/el-checkbox>
        <el-button type="success" plain :icon="Search" @click="loadOrders">鏌ヨ</el-button>
        <el-button :icon="Refresh" @click="keyword=''; includeDone=false; loadOrders()">閲嶇疆</el-button>
      </div>

      <el-table v-loading="loading" :data="orders" stripe>
        <el-table-column prop="order_no" label="閲囪喘鍗曞彿" min-width="140" />
        <el-table-column label="鏉ユ簮" min-width="145">
          <template #default="scope">
            <div class="source-cell">
              <el-tag size="small" :type="scope.row.source_type === '璁㈠崟鐢熸垚' ? 'primary' : 'info'">{{ scope.row.source_type || '閲囪喘鏂板' }}</el-tag>
              <span v-if="scope.row.source_no">{{ scope.row.source_no }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_by" label="鏂板/鎶ュ崟浜? width="110" />
        <el-table-column prop="supplier" label="渚涘簲鍟? min-width="130" />
        <el-table-column prop="purchase_date" label="閲囪喘鏃ユ湡" width="115" />
        <el-table-column label="鏄庣粏" min-width="260"><template #default="scope">{{ itemSummary(scope.row) }}</template></el-table-column>
        <el-table-column label="鍚堣" width="110"><template #default="scope">楼{{ orderTotal(scope.row).toFixed(2) }}</template></el-table-column>
        <el-table-column prop="delivery_method" label="澶勭悊鏂瑰紡" width="95" />
        <el-table-column label="鐘舵€? width="95"><template #default="scope"><el-tag :type="statusTag(scope.row.status)">{{ scope.row.status }}</el-tag></template></el-table-column>
        <el-table-column label="鎿嶄綔" width="95">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :disabled="scope.row.status === '宸插叆搴?" @click="openEdit(scope.row)">濉啓閲囪喘淇℃伅</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <el-dialog v-model="dialogVisible" title="濉啓閲囪喘淇℃伅" width="92%" top="5vh" destroy-on-close>
      <el-form label-position="top" class="purchase-form">
        <section class="form-section">
          <div class="form-grid four">
            <el-form-item label="閲囪喘鍗曞彿"><el-input v-model="form.order_no" disabled /></el-form-item>
            <el-form-item label="鏉ユ簮"><el-input :model-value="form.source_text || form.source_type || '閲囪喘鏂板'" disabled /></el-form-item>
            <el-form-item label="渚涘簲鍟?><el-input v-model="form.supplier" /></el-form-item>
            <el-form-item label="閲囪喘鏃ユ湡"><el-date-picker v-model="form.purchase_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
            <el-form-item label="澶勭悊鏂瑰紡"><el-select v-model="form.delivery_method" style="width:100%"><el-option label="鍏ュ簱" value="鍏ュ簱" /><el-option label="渚涘簲鍟嗙洿閫? value="渚涘簲鍟嗙洿閫? /><el-option label="璐ф媺鎷夌洿閫? value="璐ф媺鎷夌洿閫? /></el-select></el-form-item>
            <el-form-item label="杩愯垂"><el-input-number v-model="form.freight_fee" :min="0" :controls="false" /></el-form-item>
            <el-form-item label="璐ф媺鎷夎垂鐢?><el-input-number v-model="form.hll_fee" :min="0" :controls="false" /></el-form-item>
            <el-form-item label="澶囨敞" class="wide"><el-input v-model="form.notes" /></el-form-item>
            <el-form-item label="閲囪喘鏀舵嵁" class="wide">
              <input ref="receiptInput" type="file" accept="image/*,.pdf" class="hidden-input" @change="handleReceipt" />
              <div class="receipt-upload-line">
                <el-button type="primary" plain :icon="Upload" @click="chooseReceipt">涓婁紶鏀舵嵁</el-button>
                <span v-if="!receipts.length" class="muted">閲囪喘瀹屾垚鍓嶅繀椤讳笂浼犳敹鎹収鐗囨垨 PDF</span>
                <el-tag v-for="(file,index) in receipts" :key="index" closable @close="removeReceipt(index)">{{ file.file_name }}</el-tag>
              </div>
            </el-form-item>
            <el-form-item label="鍟嗗搧璇︽儏" class="wide">
              <input ref="detailInput" type="file" accept="image/*,.pdf" class="hidden-input" @change="handleDetail" />
              <div class="receipt-upload-line">
                <el-button type="success" plain :icon="Upload" @click="chooseDetail">涓婁紶鍟嗗搧璇︽儏</el-button>
                <span v-if="!productDetails.length" class="muted">涓婁紶鍟嗗搧瀹炵墿銆佽鏍兼爣绛俱€侀噰璐竻鍗曠瓑锛屾柟渚夸粨绠℃牳瀵?/span>
                <el-tag v-for="(file,index) in productDetails" :key="index" closable @close="removeDetail(index)">{{ file.file_name }}</el-tag>
              </div>
            </el-form-item>
          </div>
        </section>

        <section class="form-section purchase-items-section">
          <div class="section-title"><strong>瀹為檯閲囪喘鏄庣粏</strong><span>濉啓鐪熷疄閲囪喘瑙勬牸銆佹暟閲忓拰閲囪喘浠枫€?/span></div>
          <div class="purchase-item-table">
            <div class="purchase-item-row purchase-item-header"><div>鍟嗗搧</div><div>瑙勬牸/鍨嬪彿</div><div>鏁伴噺</div><div>鍗曚綅</div><div>瀹為檯閲囪喘浠?/div><div>灏忚</div><div>澶囨敞</div><div>鐘舵€?/div></div>
            <div v-for="(item,index) in form.items" :key="index" class="purchase-item-row">
              <div>{{ item.product_name }}</div>
              <div><el-select v-model="item.variant_id" filterable clearable placeholder="鍙€夎鏍? @focus="loadVariants(item.product_id)" @change="()=>handleVariantChange(item)"><el-option v-for="variant in variantCache[item.product_id] || []" :key="variant.id" :label="variantLabel(variant)" :value="variant.id" /></el-select></div>
              <div><el-input-number v-model="item.quantity" :min="0.01" :controls="false" /></div>
              <div><el-input v-model="item.unit" /></div>
              <div><el-input-number v-model="item.unit_price" :min="0" :controls="false" /></div>
              <div>楼{{ (Number(item.quantity || 0) * Number(item.unit_price || 0)).toFixed(2) }}</div>
              <div><el-input v-model="item.notes" /></div>
              <div><el-tag :type="Number(item.unit_price || 0) > 0 ? 'success' : 'warning'" size="small">{{ Number(item.unit_price || 0) > 0 ? '宸插～浠? : '寰呭～浠? }}</el-tag></div>
            </div>
          </div>
        </section>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">鍙栨秷</el-button>
        <el-button type="success" :loading="saving" @click="saveOrder">淇濆瓨閲囪喘淇℃伅</el-button>
        <el-button type="primary" :loading="saving" @click="markPurchased">淇濆瓨骞堕噰璐畬鎴?/el-button>
      </template>
    </el-dialog>
  </div>
</template>

