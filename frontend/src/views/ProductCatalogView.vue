<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Delete, Edit, Picture, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'
import { getUnitOptions } from '../utils/units'
import { useAuthStore } from '../stores/auth'

interface ProductRow {
  id: number; code: string; name: string; category: string; specification: string; unit: string
  sale_price: number; stock: number; image_url: string; image_urls: string; specification_items: string
  purchase_unit: string; base_unit: string; project_unit: string; conversion_rate: number
  project_conversion_rate: number; reference_purchase_price: number; monthly_rental_price: number
  replacement_cost_price: number; min_sale_price: number; status: string; variant_count?: number
  package_conversion_enabled: boolean
  variants?: VariantForm[]; active_variant_index?: number
}
interface VariantForm {
  id?: number; code: string; values: Record<string, string>; image_url: string
  reference_purchase_price: number | null; sale_price: number | null; monthly_rental_price: number | null
  replacement_cost_price: number | null; min_sale_price: number | null; stock: number | null; status: string
  unit: string; is_default: boolean; sort_order: number; conversion_quantity: number | null
}

const categoryOptions = ref<string[]>([])
const auth = useAuthStore()
const canDeleteProduct = computed(() => {
  const roles = String(auth.user?.role || '').replace('，', ',').split(',').map((item) => item.trim())
  return roles.some((role) => ['admin', '管理员', '经理', '老板'].includes(role)) || Boolean(auth.user?.module_permissions?.includes('system'))
})
const unitOptions = ref(getUnitOptions())
const specNameOptions = ['盆径', '高度', '冠幅']
const rows = ref<ProductRow[]>([])
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const stockVisible = ref(false)
const stockProduct = ref<ProductRow | null>(null)
const categoryDialogVisible = ref(false)
const newCategoryName = ref('')
const editingId = ref<number | null>(null)
const images = ref<string[]>([])
const specDimensions = ref<string[]>(['盆径', '高度', '冠幅'])
const variants = ref<VariantForm[]>([])
const removedVariantIds = ref<number[]>([])
const mainImageInput = ref<HTMLInputElement>()
let variantSequence = 1

function todayProductPrefix() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `SP-${year}${month}${day}`
}

function nextProductCode() {
  const prefix = todayProductPrefix()
  const usedNumbers = rows.value
    .map((row) => {
      const text = String(row.code || '')
      const match = text.match(new RegExp(`^${prefix}(\\d+)$`))
      return Number(match?.[1] || 0)
    })
    .filter((value) => Number.isFinite(value))
  const next = Math.max(0, ...usedNumbers) + 1
  return `${prefix}${next}`
}

function nextVariantCode() {
  return `${form.code || nextProductCode()}-${variantSequence++}`
}

const emptyForm = () => ({
  code: '', name: '', category: '植物', specification: '', unit: '盆',
  sale_price: 0, stock: 0, image_url: '', image_urls: '', specification_items: '', purchase_unit: '盆',
  base_unit: '盆', project_unit: '盆', conversion_rate: 1, project_conversion_rate: 1,
  reference_purchase_price: 0, monthly_rental_price: 0, replacement_cost_price: 0,
  min_sale_price: 0, package_conversion_enabled: false, status: '启用',
})
const form = reactive(emptyForm())

function parseJson<T>(value: string | undefined, fallback: T): T {
  if (!value) return fallback
  try { return JSON.parse(value) as T } catch { return fallback }
}

function optionalNumber(value: unknown): number | null {
  const number = Number(value)
  return value === null || value === undefined || value === '' || number === 0 ? null : number
}

function decimal2(value: number | null | undefined): number | null {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return null
  return Math.round((Number(value) + Number.EPSILON) * 100) / 100
}

function valueOrZero(value: number | null | undefined): number { return value ?? 0 }

function newVariant(seed?: Partial<VariantForm>): VariantForm {
  const values: Record<string, string> = {}
  specDimensions.value.forEach((name) => { values[name] = '' })
  const variant: VariantForm = {
    code: nextVariantCode(), values, image_url: '',
    reference_purchase_price: null, sale_price: null, monthly_rental_price: null,
    replacement_cost_price: null, min_sale_price: null, stock: null, status: '启用', unit: form.unit || '盆',
    conversion_quantity: null,
    is_default: variants.value.length === 0, sort_order: variants.value.length + 1, ...seed,
  }
  return variant
}

function readDimensions(row?: ProductRow): string[] {
  if (!row?.specification_items) return ['盆径', '高度', '冠幅']
  const parsed = parseJson<any[]>(row.specification_items, [])
  const allowed = new Set(specNameOptions)
  const names = parsed.map((item) => typeof item === 'string' ? item : item?.name).filter((name) => allowed.has(name))
  const merged = Array.from(new Set([...names, ...specNameOptions]))
  return merged.length ? merged : ['盆径', '高度', '冠幅']
}

function resetForm(row?: ProductRow) {
  Object.assign(form, row || emptyForm())
  images.value = row ? parseJson<string[]>(row.image_urls, row.image_url ? [row.image_url] : []).slice(0, 1) : []
  specDimensions.value = readDimensions(row)
  variants.value = []
  removedVariantIds.value = []
  variantSequence = 1
}

async function fillNextProductCode() {
  if (editingId.value || form.code) return
  try {
    const response = await api.get('/products/next-code')
    form.code = response.data.code || nextProductCode()
  } catch {
    form.code = nextProductCode()
  }
  refreshVariantCodes()
}

function refreshVariantCodes() {
  const baseCode = form.code || nextProductCode()
  variants.value.forEach((variant, index) => {
    if (!variant.id || !variant.code || /^SP-\d{8}\d+-\d+$/.test(variant.code) || /^P-\d+-\d+$/.test(variant.code)) {
      variant.code = `${baseCode}-${index + 1}`
    }
  })
  variantSequence = variants.value.length + 1
}

async function loadRows() {
  loading.value = true
  try {
    const response = await api.get('/products', { params: { keyword: keyword.value.trim() } })
    const products = response.data.items as ProductRow[]
    await Promise.all(products.map(async (row) => {
      try {
        const result = (await api.get(`/products/${row.id}/variants`)).data
        row.variant_count = result.total
        row.variants = result.items.map((item: any) => ({
          id: item.id, code: item.code, values: parseJson<Record<string, string>>(item.specification_values, {}),
          image_url: item.image_url || '', reference_purchase_price: optionalNumber(item.reference_purchase_price),
          sale_price: optionalNumber(item.sale_price), monthly_rental_price: optionalNumber(item.monthly_rental_price),
          replacement_cost_price: optionalNumber(item.replacement_cost_price), min_sale_price: optionalNumber(item.min_sale_price),
          stock: optionalNumber(item.stock), status: item.status, unit: item.unit || row.unit,
          is_default: Boolean(item.is_default), sort_order: item.sort_order ?? 100,
          conversion_quantity: optionalNumber(item.conversion_quantity),
        }))
        row.active_variant_index = row.package_conversion_enabled ? -1 : 0
      }
      catch { row.variant_count = 0 }
    }))
    rows.value = products
  } catch (error: any) { ElMessage.error(error.response?.data?.detail || '商品数据加载失败') }
  finally { loading.value = false }
}

async function loadCategories() {
  try {
    const response = await api.get('/products/categories')
    categoryOptions.value = response.data.items || []
  } catch {
    categoryOptions.value = ['植物', '花盆', '农药', '肥料', '工具', '组合盆景', '其他']
  }
}

async function addCategory() {
  const name = newCategoryName.value.trim()
  if (!name) { ElMessage.warning('请输入分类名称'); return }
  try {
    await api.post('/products/categories', { name })
    ElMessage.success('分类添加成功')
    newCategoryName.value = ''
    categoryDialogVisible.value = false
    await loadCategories()
    form.category = name
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '分类添加失败')
  }
}

async function openCreate() {
  editingId.value = null
  unitOptions.value = getUnitOptions()
  loadCategories()
  resetForm()
  variants.value = [newVariant()]
  await fillNextProductCode()
  dialogVisible.value = true
}

async function openEdit(row: ProductRow) {
  editingId.value = row.id
  unitOptions.value = getUnitOptions()
  loadCategories()
  resetForm(row)
  try {
    const response = await api.get(`/products/${row.id}/variants`)
    variants.value = response.data.items.map((item: any) => ({
      id: item.id, code: item.code, values: parseJson<Record<string, string>>(item.specification_values, {}),
      image_url: item.image_url || '', reference_purchase_price: optionalNumber(item.reference_purchase_price),
      sale_price: optionalNumber(item.sale_price), monthly_rental_price: optionalNumber(item.monthly_rental_price),
      replacement_cost_price: optionalNumber(item.replacement_cost_price), min_sale_price: optionalNumber(item.min_sale_price),
      stock: optionalNumber(item.stock), status: item.status,
      unit: item.unit || row.unit, is_default: Boolean(item.is_default), sort_order: item.sort_order ?? 100,
      conversion_quantity: optionalNumber(item.conversion_quantity),
    }))
    if (!variants.value.length) {
      const legacyValues: Record<string, string> = { [specDimensions.value[0]]: row.specification || '' }
      variants.value = [newVariant({ code: `${row.code}-1`, values: legacyValues, image_url: row.image_url,
        reference_purchase_price: row.reference_purchase_price, sale_price: row.sale_price,
        monthly_rental_price: row.monthly_rental_price, replacement_cost_price: row.replacement_cost_price,
        min_sale_price: row.min_sale_price, stock: row.stock, status: row.status })]
    }
  } catch { variants.value = [newVariant()] }
  dialogVisible.value = true
}

function addDimension() {
  const next = specNameOptions.find((item) => !specDimensions.value.includes(item))
  if (!next) { ElMessage.warning('规格只保留盆径、高度、冠幅三项'); return }
  const name = next
  specDimensions.value.push(name)
  variants.value.forEach((variant) => { variant.values[name] = '' })
}
function renameDimension(index: number, oldName: string, newName: string) {
  if (!newName || oldName === newName) return
  variants.value.forEach((variant) => { variant.values[newName] = variant.values[oldName] || ''; delete variant.values[oldName] })
}
function removeDimension(index: number) {
  if (specDimensions.value.length === 1) { ElMessage.warning('至少保留一个规格维度'); return }
  const name = specDimensions.value[index]
  specDimensions.value.splice(index, 1)
  variants.value.forEach((variant) => delete variant.values[name])
}
function addVariant() {
  variants.value.push(newVariant({ code: `${form.code || nextProductCode()}-${variants.value.length + 1}` }))
  variantSequence = variants.value.length + 1
}
function applyBundlePurchasePreset() {
  form.purchase_unit = '套'
  form.unit = '套'
  form.sale_price = 0
  form.monthly_rental_price = 0
  specDimensions.value = ['盆径', '高度', '冠幅']
  const isBlankDefault = variants.value.length === 1 && !Object.values(variants.value[0].values).some(Boolean)
  if (isBlankDefault) {
    variants.value = ['大号', '中号', '小号'].map((size, index) => newVariant({
      code: `${form.code || nextProductCode()}-${index + 1}`,
      values: { 盆径: size, 高度: '', 冠幅: '' },
      unit: '个',
      conversion_quantity: 1,
      sort_order: index + 1,
      is_default: index === 0,
    }))
  } else {
    variants.value.forEach((item) => {
      item.unit = '个'
      item.conversion_quantity = 1
    })
  }
}
function handleBundlePurchaseChange(enabled: boolean | string | number) {
  if (Boolean(enabled)) applyBundlePurchasePreset()
  else {
    form.purchase_unit = form.unit
    variants.value.forEach((item) => { item.unit = form.unit; item.conversion_quantity = 1 })
  }
}
function setDefaultVariant(index: number) { variants.value.forEach((item, itemIndex) => { item.is_default = itemIndex === index }) }
function removeVariant(index: number) {
  if (variants.value.length === 1) { ElMessage.warning('一个商品至少保留一个规格'); return }
  const item = variants.value[index]
  if (item.id) removedVariantIds.value.push(item.id)
  variants.value.splice(index, 1)
  if (!variants.value.some((variant) => variant.is_default) && variants.value.length) variants.value[0].is_default = true
}

function chooseMainImages() { mainImageInput.value?.click() }
function fileToDataUrl(file: File, done: (url: string) => void) {
  if (file.size > 2 * 1024 * 1024) { ElMessage.warning(`${file.name}超过2MB，请压缩后上传`); return }
  const reader = new FileReader(); reader.onload = () => done(String(reader.result)); reader.readAsDataURL(file)
}
function handleMainImages(event: Event) {
  const input = event.target as HTMLInputElement; const files = Array.from(input.files || [])
  const file = files[0]
  if (file) fileToDataUrl(file, (url) => { images.value = [url] })
  input.value = ''
}
function handleVariantImage(event: Event, index: number) {
  const input = event.target as HTMLInputElement; const file = input.files?.[0]
  if (file) fileToDataUrl(file, (url) => { variants.value[index].image_url = url })
  input.value = ''
}
function syncVariantImagesWithMain() {
  if (!images.value[0]) { ElMessage.warning('请先上传商品主图'); return }
  variants.value.forEach((variant) => { variant.image_url = images.value[0] })
  ElMessage.success('规格图片已同步主图')
}
function formatSpecValue(name: string, value: string) {
  const text = String(value || '').trim()
  if (!text) return ''
  if (name === '高度') return text.startsWith('高') ? text : `高${text}`
  if (name === '冠幅') return text.startsWith('宽') ? text : `宽${text}`
  return text
}
function variantSummary(item: VariantForm) {
  return specDimensions.value.map((name) => {
    const value = formatSpecValue(name, item.values[name] || '')
    return value ? `${name}：${value}` : ''
  }).filter(Boolean).join('；')
}

function variantLabel(item: VariantForm) {
  const values = specDimensions.value.map((name) => formatSpecValue(name, item.values[name] || '')).filter(Boolean)
  return values.join(' · ') || '未命名规格'
}
function activeVariant(row: ProductRow) {
  if (row.active_variant_index === -1) return null
  return row.variants?.[row.active_variant_index || 0]
}
function activeCatalogItem(row: ProductRow) {
  const variant = activeVariant(row)
  if (variant) return { label: variantLabel(variant), code: variant.code, stock: variant.stock, unit: variant.unit, image_url: variant.image_url || row.image_url }
  return { label: row.purchase_unit || row.unit, code: row.code, stock: row.stock, unit: row.purchase_unit || row.unit, image_url: row.image_url }
}
function cardImage(row: ProductRow) {
  return activeCatalogItem(row).image_url
}
function selectParent(row: ProductRow) { row.active_variant_index = -1 }
function selectVariant(row: ProductRow, index: number) { row.active_variant_index = index }
function openStock(row: ProductRow) { stockProduct.value = row; stockVisible.value = true }

async function save() {
  if (!editingId.value) refreshVariantCodes()
  if (!form.code.trim() || !form.name.trim()) { ElMessage.warning('请填写商品编码和商品名称'); return }
  if (!variants.value.length || variants.value.some((item) => !item.code.trim())) { ElMessage.warning('请填写每个规格的规格编码'); return }
  if (new Set(variants.value.map((item) => item.code.trim())).size !== variants.value.length) { ElMessage.warning('同一商品的规格编码不能重复'); return }
  if (form.package_conversion_enabled && variants.value.some((item) => !item.unit)) { ElMessage.warning('开启成套采购后，每个型号都要填写单位'); return }
  const first = variants.value[0]
  if (form.package_conversion_enabled) form.unit = form.purchase_unit
  else form.purchase_unit = form.unit
  if (form.package_conversion_enabled) {
    form.sale_price = 0
    form.monthly_rental_price = 0
  }
  form.base_unit = form.unit
  form.project_unit = form.unit
  form.project_conversion_rate = 1
  form.conversion_rate = 1
  variants.value.forEach((item) => { item.conversion_quantity = 1 })
  if (!form.package_conversion_enabled) variants.value.forEach((item) => { item.unit = form.unit })
  form.specification_items = JSON.stringify(specDimensions.value)
  form.specification = variants.value.map(variantSummary).filter(Boolean).join(' / ')
  form.image_url = images.value[0] || ''
  form.image_urls = JSON.stringify(images.value)
  if (!form.package_conversion_enabled) {
    form.reference_purchase_price = valueOrZero(first.reference_purchase_price)
    form.sale_price = valueOrZero(first.sale_price)
    form.monthly_rental_price = valueOrZero(first.monthly_rental_price)
    form.replacement_cost_price = valueOrZero(first.replacement_cost_price)
    form.min_sale_price = valueOrZero(first.min_sale_price)
    form.stock = variants.value.reduce((sum, item) => sum + Number(item.stock || 0), 0)
  }
  saving.value = true
  let newlyCreatedProductId: number | null = null
  try {
    const response = editingId.value ? await api.put(`/products/${editingId.value}`, form) : await api.post('/products', form)
    const productId = response.data.id as number
    if (!editingId.value) newlyCreatedProductId = productId
    for (const id of removedVariantIds.value) await api.delete(`/products/${productId}/variants/${id}`)
    for (const item of variants.value) {
      const payload = { code: item.code.trim(), specification: variantSummary(item), specification_values: JSON.stringify(item.values),
        image_url: item.image_url, reference_purchase_price: valueOrZero(item.reference_purchase_price), sale_price: valueOrZero(item.sale_price),
        monthly_rental_price: valueOrZero(item.monthly_rental_price), replacement_cost_price: valueOrZero(item.replacement_cost_price),
        min_sale_price: valueOrZero(item.min_sale_price), stock: valueOrZero(item.stock), status: item.status, unit: item.unit,
        is_default: item.is_default, sort_order: item.sort_order, conversion_quantity: valueOrZero(item.conversion_quantity) || 1 }
      if (item.id) await api.put(`/products/${productId}/variants/${item.id}`, payload)
      else await api.post(`/products/${productId}/variants`, payload)
    }
    ElMessage.success(`商品${editingId.value ? '修改' : '新增'}成功`)
    dialogVisible.value = false
    await loadRows()
  } catch (error: any) {
    if (newlyCreatedProductId) {
      try { await api.delete(`/products/${newlyCreatedProductId}`) } catch { /* 保留原始错误提示 */ }
    }
    ElMessage.error(error.response?.data?.detail || '保存失败，已撤销本次未完成的新商品')
  }
  finally { saving.value = false }
}

async function remove(row: ProductRow) {
  await ElMessageBox.confirm(`确定删除“${row.name}”及其全部规格吗？`, '删除确认', { type: 'warning' })
  try { await api.delete(`/products/${row.id}`); ElMessage.success('删除成功'); await loadRows() }
  catch (error: any) { ElMessage.error(error.response?.data?.detail || '删除失败') }
}

onMounted(() => {
  loadCategories()
  loadRows()
})
</script>

<template>
  <div class="page product-page">
    <div class="page-heading compact"><div><p class="eyebrow">PRODUCT CENTER</p><h1>商品管理</h1><p>一个商品主档可维护多个规格，每个规格独立管理编码、图片、价格和库存。</p></div><el-button type="success" :icon="Plus" @click="openCreate">新增商品</el-button></div>
    <article class="panel product-list-panel">
      <div class="crud-toolbar"><el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="搜索商品名称、编码或分类" @keyup.enter="loadRows" @clear="loadRows" /><el-button type="success" plain :icon="Search" @click="loadRows">查询</el-button><el-button :icon="Refresh" @click="keyword = ''; loadRows()">重置</el-button><span class="crud-count">共 {{ rows.length }} 个商品</span></div>
      <div v-loading="loading" class="product-card-grid">
        <article v-for="row in rows" :key="row.id" class="catalog-card">
          <div class="catalog-media"><el-image v-if="cardImage(row)" :src="cardImage(row)" fit="cover" /><div v-else class="catalog-image-empty"><el-icon><Picture /></el-icon><span>暂无图片</span></div></div>
          <div class="catalog-content">
            <div class="catalog-title"><span>【{{ row.category || '通用' }}】{{ row.code }}</span><strong>{{ row.name }}</strong></div>
            <div v-if="row.variants?.length" class="catalog-specs"><button v-if="row.package_conversion_enabled" type="button" class="parent-sku-button" :class="{ active: row.active_variant_index === -1 }" @click="selectParent(row)">成套采购</button><button v-for="(variant,index) in row.variants" :key="variant.id || index" type="button" :class="{ active: row.active_variant_index === index }" @click="selectVariant(row,index)">{{ variantLabel(variant) }}</button></div>
            <div class="catalog-selected"><span>已选：{{ activeCatalogItem(row).label }}</span><span>{{ activeVariant(row) ? '规格编码' : '商品编码' }} {{ activeCatalogItem(row).code }}</span><span>库存 {{ activeCatalogItem(row).stock }} {{ activeCatalogItem(row).unit }}</span></div>
            <div class="catalog-actions"><el-button type="success" :icon="Edit" @click="openEdit(row)">编辑</el-button><el-button type="success" plain @click="openStock(row)">查看库存</el-button><el-button v-if="canDeleteProduct" link type="danger" :icon="Delete" @click="remove(row)">删除</el-button></div>
          </div>
        </article>
        <el-empty v-if="!loading && !rows.length" description="暂无商品，点击右上角新增" />
      </div>
    </article>

    <el-dialog v-model="stockVisible" :title="`${stockProduct?.name || ''} · 规格库存`" width="680px">
      <div v-if="stockProduct?.package_conversion_enabled" class="parent-stock-summary">
        <span>整套库存</span>
        <strong>{{ stockProduct.stock }} {{ stockProduct.purchase_unit || stockProduct.unit }}</strong>
        <small>整套库存按各型号可凑成的完整套数计算；采购整套入库会增加所有型号，项目出单个型号会扣对应型号并重算整套库存。</small>
      </div>
      <el-table :data="stockProduct?.variants || []" stripe empty-text="暂无规格库存">
        <el-table-column label="规格"><template #default="scope"><strong>{{ variantLabel(scope.row) }}</strong></template></el-table-column><el-table-column prop="code" label="规格编码" min-width="140" /><el-table-column label="库存"><template #default="scope">{{ scope.row.stock }} {{ scope.row.unit }}</template></el-table-column><el-table-column label="状态" width="90"><template #default="scope"><el-tag :type="scope.row.status === '启用' ? 'success' : 'info'">{{ scope.row.status }}</el-tag></template></el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog v-model="categoryDialogVisible" title="添加商品分类" width="420px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="分类名称">
          <el-input v-model="newCategoryName" placeholder="例如：花盆、药肥、工具" clearable @keyup.enter="addCategory" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="categoryDialogVisible=false">取消</el-button>
        <el-button type="success" :icon="Plus" @click="addCategory">添加并选中</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dialogVisible" :title="`${editingId ? '编辑' : '新增'}商品`" width="min(1680px, calc(100vw - 120px))" class="product-editor-dialog" destroy-on-close align-center append-to-body>
      <el-form label-position="top" class="product-editor-form">
        <section class="editor-block basic-block">
          <div class="editor-block-title"><strong>基础信息</strong><span>{{ form.package_conversion_enabled ? '当前商品开启成套采购：项目可选单个型号，采购必须买整套' : '普通商品可直接在下方维护多个规格' }}</span></div>
          <div class="basic-editor-layout">
            <div class="basic-images">
              <div class="image-editor-label"><strong>商品主图</strong><span>放在最左边，录商品时先看图再填信息</span></div>
              <input ref="mainImageInput" class="hidden-input" type="file" accept="image/*" @change="handleMainImages" />
              <div class="main-image-preview" @click="chooseMainImages">
                <el-image v-if="images[0]" :src="images[0]" fit="cover" />
                <div v-else class="image-preview-empty"><el-icon><Picture /></el-icon><span>点击上传主图</span></div>
                <button v-if="images[0]" type="button" class="main-image-remove" @click.stop="images=[]">×</button>
                <span v-if="images[0]" class="main-image-badge">主图</span>
              </div>
              <el-button type="success" :icon="Plus" @click="chooseMainImages">{{ images[0] ? '更换主图' : '上传主图' }}</el-button>
            </div>
            <div class="basic-fields">
              <el-form-item label="商品分类" required>
                <div class="product-category-picker">
                  <el-select v-model="form.category" filterable allow-create style="width:100%">
                    <el-option v-for="item in categoryOptions" :key="item" :label="item" :value="item" />
                  </el-select>
                  <el-button plain type="success" :icon="Plus" @click="categoryDialogVisible = true">分类</el-button>
                </div>
              </el-form-item>
              <el-form-item label="商品名称" required><el-input v-model="form.name" placeholder="例如：小绿萝" /></el-form-item>
              <el-form-item label="商品编码" required><el-input v-model="form.code" @change="refreshVariantCodes" /><div class="field-help">自动按当天生成，例如 SP-202608201、SP-202608202</div></el-form-item>
              <el-form-item v-if="!form.package_conversion_enabled" label="商品单位" class="basic-left"><el-select v-model="form.unit" filterable allow-create style="width:100%"><el-option v-for="item in unitOptions" :key="item" :label="item" :value="item" /></el-select><div class="field-help">普通商品的库存、项目和出库统一使用此单位</div></el-form-item>
              <el-form-item v-else label="整套采购单位" required class="basic-left"><el-select v-model="form.purchase_unit" filterable allow-create style="width:100%"><el-option v-for="item in unitOptions" :key="item" :label="item" :value="item" /></el-select><div class="field-help">套盆一般选“套”，每套包含下方的大号、中号、小号</div></el-form-item>
              <el-form-item label="必须成套采购" class="basic-right"><div class="bundle-switch"><el-switch v-model="form.package_conversion_enabled" @change="handleBundlePurchaseChange" /><span>{{ form.package_conversion_enabled ? '已开启：需要其中一个型号时，也必须采购整套大/中/小' : '未开启：各规格可分开采购' }}</span></div></el-form-item>
              <el-form-item label="商品状态" class="basic-right"><el-radio-group v-model="form.status"><el-radio value="启用">启用</el-radio><el-radio value="停用">停用</el-radio></el-radio-group></el-form-item>
              <div v-if="form.package_conversion_enabled" class="conversion-guide"><strong>成套规则</strong><span>下方维护大号、中号、小号，项目可选择其中一个型号；采购需求只要涉及其中一个型号，就按整套采购。</span><small>整套总价填在规格信息上方，型号采购价人工拆分填写</small></div>
            </div>
          </div>
        </section>

        <section class="editor-block variants-block">
          <div class="editor-block-title"><strong>规格信息</strong><span>只保留盆径、高度、冠幅；高度会显示“高多少”，冠幅会显示“宽多少”。</span><el-button plain type="success" size="small" @click="syncVariantImagesWithMain">规格图片同步主图</el-button></div>
          <div v-if="form.package_conversion_enabled" class="bundle-price-row">
            <el-form-item v-if="form.package_conversion_enabled" label="整套采购价"><el-input-number v-model="form.reference_purchase_price" :min="0" :controls="false" @change="(value:number|undefined)=>form.reference_purchase_price=valueOrZero(decimal2(value))" /><div class="field-help">例如：一套大/中/小共 55 元</div></el-form-item>
            <el-form-item v-if="form.package_conversion_enabled" label="整套库存"><el-input-number v-model="form.stock" :min="0" :controls="false" @change="(value:number|undefined)=>form.stock=valueOrZero(decimal2(value))" /><div class="field-help">这里记录整套库存；下方各型号记录项目和出库使用的库存</div></el-form-item>
          </div>
          <div class="variant-table-scroll">
            <div class="variant-table">
              <div class="variant-table-row variant-table-header" :class="{'has-conversion':form.package_conversion_enabled}"><div>默认</div><div>图片</div><div>盆径 / 高度 / 冠幅</div><div>{{ form.package_conversion_enabled ? '型号编号' : '规格编码' }}</div><div>单位</div><div>{{ form.package_conversion_enabled ? '采购价' : '采购价（最新采购入库价）' }}</div><div>销售价</div><div>月租价</div><div>库存</div><div>排序</div><div>操作</div></div>
              <div v-for="(variant,index) in variants" :key="variant.id || index" class="variant-table-row" :class="{'has-conversion':form.package_conversion_enabled}">
                <div><button type="button" class="default-variant-button" :class="{active:variant.is_default}" @click="setDefaultVariant(index)">{{ variant.is_default ? '默认' : '设为默认' }}</button></div>
                <div><label class="variant-table-image"><input type="file" accept="image/*" @change="handleVariantImage($event,index)" /><el-image v-if="variant.image_url" :src="variant.image_url" fit="cover" /><template v-else><el-icon><Picture /></el-icon><small>上传</small></template></label></div>
                <div class="variant-spec-inputs"><el-input v-for="name in specDimensions" :key="name" v-model="variant.values[name]" :placeholder="name" /></div>
                <div><el-input v-model="variant.code" /></div>
                <div><el-select v-if="form.package_conversion_enabled" v-model="variant.unit" filterable allow-create><el-option v-for="item in unitOptions" :key="item" :label="item" :value="item" /></el-select><span v-else class="variant-unit-text">{{ form.unit }}</span></div>
                <div class="purchase-price-cell"><el-input-number v-model="variant.reference_purchase_price" :min="0" :controls="false" :disabled="!form.package_conversion_enabled" @change="(value:number|undefined)=>variant.reference_purchase_price=decimal2(value)" /></div>
                <div><el-input-number v-model="variant.sale_price" :min="0" :controls="false" @change="(value:number|undefined)=>variant.sale_price=decimal2(value)" /></div>
                <div><el-input-number v-model="variant.monthly_rental_price" :min="0" :controls="false" @change="(value:number|undefined)=>variant.monthly_rental_price=decimal2(value)" /></div>
                <div><el-input-number v-model="variant.stock" :min="0" :controls="false" @change="(value:number|undefined)=>variant.stock=decimal2(value)" /></div>
                <div><el-input-number v-model="variant.sort_order" :min="0" :precision="0" :controls="false" /></div>
                <div><el-button link type="danger" :icon="Delete" @click="removeVariant(index)">删除</el-button></div>
              </div>
            </div>
          </div>
          <div class="add-variant-bar"><el-button type="success" :icon="Plus" @click="addVariant">添加规格</el-button></div>
        </section>
      </el-form>
      <template #footer><div class="editor-footer"><el-button @click="dialogVisible=false">返回</el-button><el-button type="success" :loading="saving" @click="save">保存商品</el-button></div></template>
    </el-dialog>
  </div>
</template>
