<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ArrowDown, Delete, Edit, Picture, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

interface SpecItem { name: string; value: string }
interface ProductRow {
  id: number; code: string; name: string; category: string; specification: string; unit: string
  sale_price: number; stock: number; image_url: string; image_urls: string; specification_items: string
  purchase_unit: string; base_unit: string; project_unit: string; conversion_rate: number
  project_conversion_rate: number; reference_purchase_price: number; monthly_rental_price: number
  replacement_cost_price: number; min_sale_price: number; status: string
}

const categoryOptions = ['妞嶇墿', '瑁呴グ鑺辩泦', '鍐滆嵂', '鑲ユ枡', '宸ュ叿', '缁勫悎鐩嗘櫙', '鍏朵粬']
const unitOptions = ['鐩?, '涓?, '妫?, '绠?, '鐡?, '琚?, '鏂?, '鍏枻', '濂?, '浠?]
const specNameOptions = ['楂樺害', '绮楀害', '鍐犲箙', '鍩哄湴绉嶆鐩?, '鐩嗗緞', '棰滆壊', '鍏朵粬']
const rows = ref<ProductRow[]>([])
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const images = ref<string[]>([])
const specs = ref<SpecItem[]>([])
const imageInput = ref<HTMLInputElement>()

const emptyForm = () => ({
  code: `SP-${Date.now().toString().slice(-8)}`, name: '', category: '妞嶇墿', specification: '', unit: '鐩?,
  sale_price: 0, stock: 0, image_url: '', image_urls: '', specification_items: '', purchase_unit: '鐩?,
  base_unit: '鐩?, project_unit: '鐩?, conversion_rate: 1, project_conversion_rate: 1,
  reference_purchase_price: 0, monthly_rental_price: 0, replacement_cost_price: 0,
  min_sale_price: 0, status: '鍚敤',
})
const form = reactive(emptyForm())

function parseJson<T>(value: string | undefined, fallback: T): T {
  if (!value) return fallback
  try { return JSON.parse(value) as T } catch { return fallback }
}

function resetForm(row?: ProductRow) {
  Object.assign(form, row || emptyForm())
  specs.value = row ? parseJson<SpecItem[]>(row.specification_items, row.specification ? [{ name: '瑙勬牸', value: row.specification }] : []) : [{ name: '楂樺害', value: '' }]
  images.value = row ? parseJson<string[]>(row.image_urls, row.image_url ? [row.image_url] : []) : []
}

async function loadRows() {
  loading.value = true
  try {
    const response = await api.get('/products', { params: { keyword: keyword.value.trim() } })
    rows.value = response.data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鍟嗗搧鏁版嵁鍔犺浇澶辫触')
  } finally { loading.value = false }
}

function openCreate() { editingId.value = null; resetForm(); dialogVisible.value = true }
function openEdit(row: ProductRow) { editingId.value = row.id; resetForm(row); dialogVisible.value = true }
function addSpec() { specs.value.push({ name: '', value: '' }) }
function removeSpec(index: number) { specs.value.splice(index, 1) }

function chooseImages() { imageInput.value?.click() }
function handleImages(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (images.value.length + files.length > 6) { ElMessage.warning('姣忎釜鍟嗗搧鏈€澶氫笂浼?寮犲浘鐗?); input.value = ''; return }
  files.forEach((file) => {
    if (file.size > 2 * 1024 * 1024) { ElMessage.warning(`${file.name}瓒呰繃2MB锛屽凡璺宠繃`); return }
    const reader = new FileReader()
    reader.onload = () => images.value.push(String(reader.result))
    reader.readAsDataURL(file)
  })
  input.value = ''
}

async function save() {
  if (!form.code.trim() || !form.name.trim()) { ElMessage.warning('璇峰～鍐欏晢鍝佺紪鐮佸拰鍟嗗搧鍚嶇О'); return }
  const cleanSpecs = specs.value.filter((item) => item.name.trim() && item.value.trim())
  form.specification = cleanSpecs.map((item) => `${item.name}锛?{item.value}`).join('锛?)
  form.specification_items = JSON.stringify(cleanSpecs)
  form.image_url = images.value[0] || ''
  form.image_urls = JSON.stringify(images.value)
  saving.value = true
  try {
    if (editingId.value) await api.put(`/products/${editingId.value}`, form)
    else await api.post('/products', form)
    ElMessage.success(`鍟嗗搧${editingId.value ? '淇敼' : '鏂板'}鎴愬姛`)
    dialogVisible.value = false
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '淇濆瓨澶辫触锛岃妫€鏌ュ～鍐欏唴瀹?)
  } finally { saving.value = false }
}

async function remove(row: ProductRow) {
  await ElMessageBox.confirm(`纭畾鍒犻櫎鈥?{row.name}鈥濆悧锛焋, '鍒犻櫎纭', { type: 'warning' })
  try { await api.delete(`/products/${row.id}`); ElMessage.success('鍒犻櫎鎴愬姛'); await loadRows() }
  catch (error: any) { ElMessage.error(error.response?.data?.detail || '鍒犻櫎澶辫触') }
}

loadRows()
</script>

<template>
  <div class="page product-page">
    <div class="page-heading compact">
      <div><p class="eyebrow">PRODUCT CENTER</p><h1>鍟嗗搧绠＄悊</h1><p>缁熶竴绠＄悊妞嶇墿銆佽姳鐩嗐€佽嵂鍝併€佽偉鏂欏拰宸ュ叿锛屾敮鎸佸浘鐗囥€佽嚜瀹氫箟瑙勬牸涓庡崟浣嶆崲绠椼€?/p></div>
      <el-button type="success" :icon="Plus" @click="openCreate">鏂板鍟嗗搧</el-button>
    </div>

    <article class="panel table-panel">
      <div class="crud-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="鎼滅储鍟嗗搧鍚嶇О銆佺紪鐮佹垨鍒嗙被" @keyup.enter="loadRows" @clear="loadRows" />
        <el-button type="success" plain :icon="Search" @click="loadRows">鏌ヨ</el-button>
        <el-button :icon="Refresh" @click="keyword = ''; loadRows()">閲嶇疆</el-button>
        <span class="crud-count">鍏?{{ rows.length }} 鏉?/span>
      </div>
      <el-table v-loading="loading" :data="rows" stripe empty-text="鏆傛棤鍟嗗搧锛岀偣鍑诲彸涓婅鏂板">
        <el-table-column label="鍥剧墖" width="78">
          <template #default="scope"><el-image v-if="scope.row.image_url" class="product-thumb" :src="scope.row.image_url" fit="cover" /><div v-else class="product-empty"><el-icon><Picture /></el-icon></div></template>
        </el-table-column>
        <el-table-column prop="code" label="鍟嗗搧缂栫爜" min-width="120" />
        <el-table-column prop="name" label="鍟嗗搧鍚嶇О" min-width="150" />
        <el-table-column prop="category" label="鍒嗙被" width="105" />
        <el-table-column prop="specification" label="瑙勬牸" min-width="180"><template #default="scope">{{ scope.row.specification || '鈥? }}</template></el-table-column>
        <el-table-column label="鍗曚綅" min-width="150"><template #default="scope">{{ scope.row.purchase_unit }} 鈫?{{ scope.row.base_unit }} 鈫?{{ scope.row.project_unit }}</template></el-table-column>
        <el-table-column prop="reference_purchase_price" label="鍙傝€冮噰璐环" width="115"><template #default="scope">楼{{ Number(scope.row.reference_purchase_price).toFixed(2) }}</template></el-table-column>
        <el-table-column prop="sale_price" label="閿€鍞环" width="105"><template #default="scope">楼{{ Number(scope.row.sale_price).toFixed(2) }}</template></el-table-column>
        <el-table-column prop="stock" label="褰撳墠搴撳瓨" width="95" />
        <el-table-column label="鐘舵€? width="80"><template #default="scope"><el-tag :type="scope.row.status === '鍚敤' ? 'success' : 'info'">{{ scope.row.status }}</el-tag></template></el-table-column>
        <el-table-column label="鎿嶄綔" width="95"><template #default="scope"><el-dropdown trigger="click"><el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item :icon="Edit" @click="openEdit(scope.row)">缂栬緫</el-dropdown-item><el-dropdown-item :icon="Delete" divided @click="remove(scope.row)">鍒犻櫎</el-dropdown-item></el-dropdown-menu></template></el-dropdown></template></el-table-column>
      </el-table>
    </article>

    <el-dialog v-model="dialogVisible" :title="`${editingId ? '缂栬緫' : '鏂板'}鍟嗗搧`" width="880px" destroy-on-close>
      <el-form label-position="top" class="product-form">
        <section class="form-section">
          <div class="section-title"><strong>鍩烘湰璧勬枡</strong><span>鍟嗗搧鍜岀墿鏂欑粺涓€缁存姢锛岄€氳繃鍒嗙被鍖哄垎</span></div>
          <div class="form-grid three">
            <el-form-item label="鍟嗗搧缂栫爜" required><el-input v-model="form.code" /></el-form-item>
            <el-form-item label="鍟嗗搧鍚嶇О" required><el-input v-model="form.name" /></el-form-item>
            <el-form-item label="鍟嗗搧鍒嗙被"><el-select v-model="form.category" filterable allow-create style="width:100%"><el-option v-for="item in categoryOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item>
            <el-form-item label="褰撳墠搴撳瓨"><el-input-number v-model="form.stock" :min="0" :precision="0" style="width:100%" /></el-form-item>
            <el-form-item label="鏄剧ず鍗曚綅"><el-select v-model="form.unit" filterable allow-create style="width:100%"><el-option v-for="item in unitOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item>
            <el-form-item label="鐘舵€?><el-select v-model="form.status" style="width:100%"><el-option label="鍚敤" value="鍚敤" /><el-option label="鍋滅敤" value="鍋滅敤" /></el-select></el-form-item>
          </div>
        </section>

        <section class="form-section">
          <div class="section-title"><strong>鍟嗗搧鍥剧墖</strong><span>绗竴寮犱綔涓轰富鍥撅紝鏈€澶?寮狅紝姣忓紶涓嶈秴杩?MB</span></div>
          <input ref="imageInput" class="hidden-input" type="file" accept="image/*" multiple @change="handleImages" />
          <div class="image-list"><div v-for="(url, index) in images" :key="index" class="image-card"><el-image :src="url" fit="cover" /><span v-if="index === 0">涓诲浘</span><button type="button" @click="images.splice(index, 1)">脳</button></div><button v-if="images.length < 6" type="button" class="image-add" @click="chooseImages"><el-icon><Plus /></el-icon><small>閫夋嫨鍥剧墖</small></button></div>
        </section>

        <section class="form-section">
          <div class="section-title"><strong>鍔ㄦ€佽鏍?/strong><span>渚嬪锛氶珮搴?1.8M銆佸啝骞?80cm銆佸熀鍦扮妞嶇泦 绂忓瓧鐩嗗ぇ鍙?/span><el-button link type="success" :icon="Plus" @click="addSpec">澧炲姞瑙勬牸椤?/el-button></div>
          <div v-for="(item, index) in specs" :key="index" class="spec-row"><el-select v-model="item.name" filterable allow-create placeholder="瑙勬牸鍚嶇О"><el-option v-for="name in specNameOptions" :key="name" :label="name" :value="name" /></el-select><el-input v-model="item.value" placeholder="瑙勬牸鍊? /><el-button circle plain type="danger" :icon="Delete" @click="removeSpec(index)" /></div>
        </section>

        <section class="form-section">
          <div class="section-title"><strong>鍗曚綅鎹㈢畻</strong><span>閲囪喘鍗曚綅 鈫?搴撳瓨鍗曚綅 鈫?椤圭洰浣跨敤鍗曚綅</span></div>
          <div class="conversion-row">
            <el-form-item label="閲囪喘鍗曚綅"><el-select v-model="form.purchase_unit" filterable allow-create><el-option v-for="item in unitOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item>
            <div class="conversion-symbol">1 {{ form.purchase_unit }} =</div>
            <el-form-item label="搴撳瓨鏁伴噺"><el-input-number v-model="form.conversion_rate" :min="0.01" :precision="2" /></el-form-item>
            <el-form-item label="搴撳瓨鍗曚綅"><el-select v-model="form.base_unit" filterable allow-create><el-option v-for="item in unitOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item>
          </div>
          <div class="conversion-row second">
            <div></div><div class="conversion-symbol">1 {{ form.project_unit }} =</div>
            <el-form-item label="鎶樺悎搴撳瓨鏁伴噺"><el-input-number v-model="form.project_conversion_rate" :min="0.01" :precision="2" /></el-form-item>
            <el-form-item label="椤圭洰浣跨敤鍗曚綅"><el-select v-model="form.project_unit" filterable allow-create><el-option v-for="item in unitOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item>
          </div>
        </section>

        <section class="form-section">
          <div class="section-title"><strong>鍙傝€冧环鏍?/strong><span>瀹為檯涓氬姟淇濆瓨鎴愪氦鎴栭噰璐壒娆′环鏍硷紝涓嶄細琚繖閲屽悗缁慨鏀硅鐩?/span></div>
          <div class="form-grid prices">
            <el-form-item label="鍙傝€冮噰璐环"><el-input-number v-model="form.reference_purchase_price" :min="0" :precision="2" style="width:100%" /></el-form-item>
            <el-form-item label="閿€鍞环"><el-input-number v-model="form.sale_price" :min="0" :precision="2" style="width:100%" /></el-form-item>
            <el-form-item label="鏈€浣庨攢鍞环"><el-input-number v-model="form.min_sale_price" :min="0" :precision="2" style="width:100%" /></el-form-item>
            <el-form-item label="鏈堢鍙傝€冧环"><el-input-number v-model="form.monthly_rental_price" :min="0" :precision="2" style="width:100%" /></el-form-item>
            <el-form-item label="鎹㈣姳鎴愭湰浠?><el-input-number v-model="form.replacement_cost_price" :min="0" :precision="2" style="width:100%" /></el-form-item>
          </div>
        </section>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">鍙栨秷</el-button><el-button type="success" :loading="saving" @click="save">淇濆瓨鍟嗗搧</el-button></template>
    </el-dialog>
  </div>
</template>

