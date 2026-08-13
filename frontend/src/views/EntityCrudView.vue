<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDown, Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'
import { permissionOptions } from '../config/menu'
import { getDepartmentOptions } from '../utils/departments'
import { getPositionOptions } from '../utils/positions'

type EntityKind = 'product' | 'customer' | 'employee'
type FieldType = 'text' | 'number' | 'select' | 'multi-select' | 'date' | 'textarea' | 'switch' | 'password'
type Row = Record<string, any>

interface FieldConfig {
  key: string
  label: string
  type?: FieldType
  required?: boolean
  options?: string[]
  default?: string | number | boolean | null
  width?: number
  prefix?: string
  table?: boolean
  placeholder?: string
}

interface EntityConfig {
  title: string
  eyebrow: string
  description: string
  singular: string
  endpoint: string
  statusActive: string
  fields: FieldConfig[]
}

const customerFields: FieldConfig[] = [
  { key: 'customer_type', label: '瀹㈡埛绫诲瀷', type: 'select', options: ['椤圭洰瀹㈡埛', '浼佷笟瀹㈡埛', '涓汉瀹㈡埛'], default: '椤圭洰瀹㈡埛', width: 110 },
  { key: 'name', label: '瀹㈡埛鍚嶇О', required: true, width: 170 },
  { key: 'project_name', label: '椤圭洰鍚嶇О', width: 170 },
  { key: 'contact_person', label: '璐熻矗浜哄悕绉?, width: 120 },
  { key: 'phone', label: '鑱旂郴鐢佃瘽', width: 135 },
  { key: 'address', label: '鍦板潃', type: 'textarea', width: 220 },
  { key: 'area', label: '鍖哄煙', width: 100 },
  { key: 'supervisor_name', label: '涓荤鍚嶇О', width: 110 },
  { key: 'supervisor_phone', label: '涓荤鐢佃瘽', width: 135 },
  { key: 'maintainer_name', label: '鍏绘姢鍛樺悕绉?, width: 110 },
  { key: 'maintainer_phone', label: '鍏绘姢鍛樼數璇?, width: 135 },
  { key: 'status', label: '鐘舵€?, type: 'select', options: ['鍚敤', '鍋滅敤'], default: '鍚敤', width: 90 },
]

const configs: Record<EntityKind, EntityConfig> = {
  product: {
    title: '鍟嗗搧绠＄悊',
    eyebrow: 'PRODUCTS',
    singular: '鍟嗗搧',
    endpoint: '/products',
    statusActive: '鍚敤',
    description: '鍟嗗搧涓绘。鐢ㄤ簬鍩虹璧勬枡缁存姢锛涜缁嗗瑙勬牸璇峰埌鍟嗗搧绠＄悊涓撻〉鎿嶄綔銆?,
    fields: [
      { key: 'code', label: '鍟嗗搧缂栫爜', required: true, width: 130 },
      { key: 'name', label: '鍟嗗搧鍚嶇О', required: true, width: 170 },
      { key: 'category', label: '鍟嗗搧鍒嗙被', default: '鏈垎绫?, width: 110 },
      { key: 'specification', label: '瑙勬牸', width: 110 },
      { key: 'unit', label: '鍗曚綅', default: '浠?, width: 80 },
      { key: 'sale_price', label: '閿€鍞环', type: 'number', default: 0, prefix: '锟?, width: 110 },
      { key: 'stock', label: '搴撳瓨', type: 'number', default: 0, width: 90 },
      { key: 'status', label: '鐘舵€?, type: 'select', options: ['鍚敤', '鍋滅敤'], default: '鍚敤', width: 90 },
    ],
  },
  customer: {
    title: '瀹㈡埛绠＄悊',
    eyebrow: 'CUSTOMERS',
    singular: '瀹㈡埛',
    endpoint: '/customers',
    statusActive: '鍚敤',
    description: '缁存姢瀹㈡埛銆侀」鐩€佸尯鍩熶富绠″拰鍏绘姢鍛樹俊鎭紱鍑哄崟鎵撳嵃鏃朵紭鍏堜娇鐢ㄥ吇鎶ゅ憳鐢佃瘽銆?,
    fields: customerFields,
  },
  employee: {
    title: '鍛樺伐绠＄悊',
    eyebrow: 'EMPLOYEES',
    singular: '鍛樺伐',
    endpoint: '/employees',
    statusActive: '鍦ㄨ亴',
    description: '缁存姢鍛樺伐鑱旂郴鏂瑰紡銆佸矖浣嶃€佽鑹层€佺櫥褰曟潈闄愬拰鍦ㄨ亴鐘舵€併€?,
    fields: [
      { key: 'name', label: '鍛樺伐濮撳悕', required: true, width: 130 },
      { key: 'phone', label: '鑱旂郴鐢佃瘽', width: 140 },
      { key: 'position', label: '宀椾綅', width: 120 },
      { key: 'department', label: '閮ㄩ棬', type: 'select', options: ['甯傚満閮?, '缁垮寲閮?, '璐㈠姟閮?, '绠＄悊灞?, '鍏朵粬'], width: 110 },
      { key: 'module_permissions', label: '妯″潡鏉冮檺', type: 'multi-select', options: permissionOptions.map((item) => item.value), table: false },
      { key: 'product_category_permissions', label: '鍟嗗搧绠＄悊-鍟嗗搧鍒嗙被鏉冮檺', type: 'multi-select', options: [], table: false },
      { key: 'hire_date', label: '鍏ヨ亴鏃ユ湡', type: 'date', width: 120 },
      { key: 'leave_date', label: '绂昏亴鏃ユ湡', type: 'date', table: false },
      { key: 'login_enabled', label: '鍚敤绯荤粺鐧诲綍', type: 'switch', default: false, table: false },
      { key: 'login_password', label: '鐧诲綍瀵嗙爜', type: 'password', table: false },
      { key: 'responsibility', label: '椤圭洰涓庡尯鍩熻亴璐?, type: 'textarea', table: false },
      { key: 'status', label: '鐘舵€?, type: 'select', options: ['鍦ㄨ亴', '鍋滅敤', '绂昏亴'], default: '鍦ㄨ亴', width: 90 },
    ],
  },
}

const route = useRoute()
const entity = computed(() => (route.meta.entity || 'product') as EntityKind)
const config = computed(() => configs[entity.value])
const tableFields = computed(() => config.value.fields.filter((field) => field.table !== false))
const visibleFormFields = computed(() => config.value.fields.filter((field) => {
  if (entity.value === 'customer' && field.key === 'project_name') return form.customer_type !== '涓汉瀹㈡埛'
  return true
}))

const rows = ref<Row[]>([])
const employees = ref<Row[]>([])
const areaSettings = ref<Row[]>([])
const productCategories = ref<string[]>([])
const positionOptions = ref<string[]>(getPositionOptions())
const departmentOptions = ref<string[]>(getDepartmentOptions())
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const areaDialogVisible = ref(false)
const editingId = ref<number | null>(null)
const areaEditingId = ref<number | null>(null)
const form = reactive<Row>({})
const areaForm = reactive<Row>({ area: '', supervisor_name: '', supervisor_phone: '', status: '鍚敤' })

const permissionLabelMap = Object.fromEntries(permissionOptions.map((item) => [item.value, item.label]))
const supervisorOptions = computed(() => employees.value.filter((item) => `${item.position},${item.role},${item.business_roles}`.includes('涓荤') || `${item.position},${item.role}`.includes('缁忕悊')))
const maintainerOptions = computed(() => employees.value.filter((item) => `${item.position},${item.role},${item.business_roles}`.includes('鍏绘姢')))

function resetForm(row?: Row) {
  Object.keys(form).forEach((key) => delete form[key])
  config.value.fields.forEach((field) => {
    if (field.type === 'multi-select') {
      const raw = row ? row[field.key] : field.default
      form[field.key] = Array.isArray(raw) ? raw : String(raw || '').split(',').map((item) => item.trim()).filter(Boolean)
    } else {
      form[field.key] = row ? (row[field.key] ?? '') : (field.default ?? '')
    }
  })
}

function resetAreaForm(row?: Row) {
  areaEditingId.value = row?.id ? Number(row.id) : null
  areaForm.area = row?.area || ''
  areaForm.supervisor_name = row?.supervisor_name || ''
  areaForm.supervisor_phone = row?.supervisor_phone || ''
  areaForm.status = row?.status || '鍚敤'
}

async function loadRows() {
  loading.value = true
  try {
    const response = await api.get(config.value.endpoint, { params: { keyword: keyword.value.trim() } })
    rows.value = response.data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鏁版嵁鍔犺浇澶辫触')
  } finally {
    loading.value = false
  }
}

async function loadEmployees() {
  if (entity.value !== 'customer') return
  try {
    employees.value = (await api.get('/employees')).data.items || []
  } catch {
    employees.value = []
  }
}

async function loadAreaSettings() {
  if (entity.value !== 'customer') return
  try {
    areaSettings.value = (await api.get('/customers/area-settings')).data.items || []
  } catch {
    areaSettings.value = []
  }
}

async function loadProductCategories() {
  if (entity.value !== 'employee') return
  try {
    productCategories.value = (await api.get('/products/categories')).data.items || []
    const field = configs.employee.fields.find((item) => item.key === 'product_category_permissions')
    if (field) field.options = productCategories.value
  } catch {
    productCategories.value = []
  }
}

function loadPositionOptions() {
  if (entity.value !== 'employee') return
  positionOptions.value = getPositionOptions()
  departmentOptions.value = getDepartmentOptions()
  const field = configs.employee.fields.find((item) => item.key === 'position')
  if (field) {
    field.type = 'select'
    field.options = positionOptions.value
  }
  const departmentField = configs.employee.fields.find((item) => item.key === 'department')
  if (departmentField) {
    departmentField.type = 'select'
    departmentField.options = departmentOptions.value
  }
}

function openCreate() {
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEdit(row: Row) {
  editingId.value = Number(row.id)
  resetForm(row)
  dialogVisible.value = true
}

function openAreaDialog() {
  resetAreaForm()
  areaDialogVisible.value = true
}

function handleAreaChange(area: string) {
  const setting = areaSettings.value.find((item) => item.area === area)
  if (!setting) return
  form.supervisor_name = setting.supervisor_name || ''
  form.supervisor_phone = setting.supervisor_phone || ''
}

function handleSupervisorChange(name: string) {
  const employee = employees.value.find((item) => item.name === name)
  if (employee) form.supervisor_phone = employee.phone || ''
}

function handleMaintainerChange(name: string) {
  const employee = employees.value.find((item) => item.name === name)
  if (employee) form.maintainer_phone = employee.phone || ''
}

function handleAreaSupervisorChange(name: string) {
  const employee = employees.value.find((item) => item.name === name)
  if (employee) areaForm.supervisor_phone = employee.phone || ''
}

async function saveAreaSetting() {
  if (!String(areaForm.area || '').trim()) {
    ElMessage.warning('璇峰～鍐欏尯鍩熷悕绉?)
    return
  }
  try {
    const payload = { ...areaForm, area: String(areaForm.area).trim() }
    if (areaEditingId.value) await api.put(`/customers/area-settings/${areaEditingId.value}`, payload)
    else await api.post('/customers/area-settings', payload)
    ElMessage.success(`鍖哄煙璁剧疆宸?{areaEditingId.value ? '淇敼' : '鏂板'}`)
    resetAreaForm()
    await loadAreaSettings()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鍖哄煙璁剧疆淇濆瓨澶辫触')
  }
}

async function removeAreaSetting(row: Row) {
  await ElMessageBox.confirm(`纭畾鍒犻櫎鍖哄煙鈥?{row.area}鈥濆悧锛焋, '鍒犻櫎纭', { type: 'warning' })
  try {
    await api.delete(`/customers/area-settings/${row.id}`)
    ElMessage.success('鍖哄煙璁剧疆鍒犻櫎鎴愬姛')
    await loadAreaSettings()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鍖哄煙璁剧疆鍒犻櫎澶辫触')
  }
}

async function save() {
  const missing = visibleFormFields.value.find((field) => field.required && !String(form[field.key] ?? '').trim())
  if (missing) {
    ElMessage.warning(`璇峰～鍐?{missing.label}`)
    return
  }
  saving.value = true
  try {
    const payload = { ...form }
    if (entity.value === 'customer' && payload.customer_type === '涓汉瀹㈡埛') payload.project_name = ''
    config.value.fields.filter((field) => field.type === 'multi-select').forEach((field) => {
      payload[field.key] = Array.isArray(payload[field.key]) ? payload[field.key].join(',') : String(payload[field.key] || '')
    })
    config.value.fields.filter((field) => field.type === 'date').forEach((field) => {
      if (!payload[field.key]) payload[field.key] = null
    })
    if (editingId.value) await api.put(`${config.value.endpoint}/${editingId.value}`, payload)
    else await api.post(config.value.endpoint, payload)
    ElMessage.success(`${config.value.singular}${editingId.value ? '淇敼' : '鏂板'}鎴愬姛`)
    dialogVisible.value = false
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '淇濆瓨澶辫触锛岃妫€鏌ュ～鍐欏唴瀹?)
  } finally {
    saving.value = false
  }
}

async function remove(row: Row) {
  await ElMessageBox.confirm(`纭畾鍒犻櫎鈥?{row.name}鈥濆悧锛熷垹闄ゅ悗涓嶅彲鎭㈠銆俙, '鍒犻櫎纭', { type: 'warning' })
  try {
    await api.delete(`${config.value.endpoint}/${row.id}`)
    ElMessage.success('鍒犻櫎鎴愬姛')
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鍒犻櫎澶辫触')
  }
}

function displayValue(row: Row, field: FieldConfig) {
  if (entity.value === 'customer' && field.key === 'project_name' && row.customer_type === '涓汉瀹㈡埛') return '鈥?
  const value = row[field.key]
  if (field.prefix && value !== '' && value !== null && value !== undefined) return `${field.prefix}${Number(value).toFixed(2)}`
  return value || '鈥?
}

watch(entity, async () => {
  keyword.value = ''
  loadPositionOptions()
  await Promise.all([loadRows(), loadEmployees(), loadAreaSettings(), loadProductCategories()])
}, { immediate: true })
</script>

<template>
  <div class="page crud-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">{{ config.eyebrow }}</p>
        <h1>{{ config.title }}</h1>
        <p>{{ config.description }}</p>
      </div>
      <div style="display:flex;gap:8px;">
        <el-button v-if="entity === 'customer'" plain type="success" @click="openAreaDialog">鍖哄煙璁剧疆</el-button>
        <el-button type="success" :icon="Plus" @click="openCreate">鏂板{{ config.singular }}</el-button>
      </div>
    </div>

    <article class="panel table-panel">
      <div class="crud-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" :placeholder="`鎼滅储${config.singular}鍚嶇О銆佺數璇濄€侀」鐩垨鍖哄煙`" @keyup.enter="loadRows" @clear="loadRows" />
        <el-button type="success" plain :icon="Search" @click="loadRows">鏌ヨ</el-button>
        <el-button :icon="Refresh" @click="keyword = ''; loadRows()">閲嶇疆</el-button>
        <span class="crud-count">鍏?{{ rows.length }} 鏉?/span>
      </div>

      <el-table v-loading="loading" :data="rows" stripe empty-text="鏆傛棤鏁版嵁锛岀偣鍑诲彸涓婅鏂板">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column v-for="field in tableFields" :key="field.key" :prop="field.key" :label="field.label" :min-width="field.width">
          <template #default="scope">
            <el-tag v-if="field.key === 'status'" :type="scope.row.status === config.statusActive ? 'success' : 'info'" effect="light">{{ scope.row.status }}</el-tag>
            <span v-else>{{ displayValue(scope.row, field) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="鎿嶄綔" width="95">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="openEdit(scope.row)">缂栬緫</el-dropdown-item>
                  <el-dropdown-item divided @click="remove(scope.row)">鍒犻櫎</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <el-dialog v-model="dialogVisible" :title="`${editingId ? '缂栬緫' : '鏂板'}${config.singular}`" width="760px" destroy-on-close>
      <el-form v-if="entity === 'customer'" label-position="top" class="customer-crud-form">
        <el-form-item label="瀹㈡埛绫诲瀷" :class="{ full: form.customer_type !== '涓汉瀹㈡埛' }">
          <el-select v-model="form.customer_type" style="width:100%">
            <el-option label="椤圭洰瀹㈡埛" value="椤圭洰瀹㈡埛" />
            <el-option label="浼佷笟瀹㈡埛" value="浼佷笟瀹㈡埛" />
            <el-option label="涓汉瀹㈡埛" value="涓汉瀹㈡埛" />
          </el-select>
        </el-form-item>
        <el-form-item label="瀹㈡埛鍚嶇О" required>
          <el-input v-model="form.name" placeholder="璇疯緭鍏ュ鎴峰悕绉? />
        </el-form-item>
        <el-form-item v-if="form.customer_type !== '涓汉瀹㈡埛'" label="椤圭洰鍚嶇О">
          <el-input v-model="form.project_name" placeholder="璇疯緭鍏ラ」鐩悕绉? />
        </el-form-item>

        <el-form-item label="璐熻矗浜哄悕绉?>
          <el-input v-model="form.contact_person" placeholder="璇疯緭鍏ヨ礋璐ｄ汉鍚嶇О" />
        </el-form-item>
        <el-form-item label="鑱旂郴鐢佃瘽">
          <el-input v-model="form.phone" placeholder="璇疯緭鍏ヨ仈绯荤數璇? />
        </el-form-item>
        <el-form-item label="鍦板潃" class="full">
          <el-input v-model="form.address" type="textarea" :rows="3" placeholder="璇疯緭鍏ュ湴鍧€" />
        </el-form-item>

        <el-form-item label="鍖哄煙">
          <div style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;width:100%;">
            <el-select v-model="form.area" filterable allow-create clearable placeholder="閫夋嫨鎴栬緭鍏ュ尯鍩? @change="handleAreaChange">
              <el-option v-for="item in areaSettings" :key="item.id" :label="`${item.area} 路 ${item.supervisor_name || '鏈涓荤'}`" :value="item.area" />
            </el-select>
            <el-button plain type="success" @click="openAreaDialog">璁剧疆</el-button>
          </div>
        </el-form-item>
        <el-form-item label="瀹㈡埛鐘舵€?>
          <el-select v-model="form.status" style="width:100%">
            <el-option label="鍚敤" value="鍚敤" />
            <el-option label="鍋滅敤" value="鍋滅敤" />
          </el-select>
        </el-form-item>

        <el-form-item label="涓荤鍚嶇О">
          <el-select v-model="form.supervisor_name" filterable allow-create clearable style="width:100%" placeholder="閫夋嫨鎴栬緭鍏ヤ富绠? @change="handleSupervisorChange">
            <el-option v-for="employee in supervisorOptions" :key="employee.id" :label="employee.name" :value="employee.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="涓荤鐢佃瘽">
          <el-input v-model="form.supervisor_phone" placeholder="閫夋嫨鍖哄煙鍚庤嚜鍔ㄥ甫鍑猴紝涔熷彲鎵嬪～" />
        </el-form-item>

        <el-form-item label="鍏绘姢鍛樺悕绉?>
          <el-select v-model="form.maintainer_name" filterable allow-create clearable style="width:100%" placeholder="閫夋嫨鎴栬緭鍏ュ吇鎶ゅ憳" @change="handleMaintainerChange">
            <el-option v-for="employee in maintainerOptions" :key="employee.id" :label="employee.name" :value="employee.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="鍏绘姢鍛樼數璇?>
          <el-input v-model="form.maintainer_phone" placeholder="閫夋嫨鍏绘姢鍛樺悗鑷姩甯﹀嚭锛屼篃鍙墜濉? />
        </el-form-item>
      </el-form>

      <el-form v-else label-position="top" class="crud-form">
        <el-form-item v-for="field in visibleFormFields" :key="field.key" :label="field.label" :required="field.required" :class="{ wide: field.type === 'textarea' }">
          <el-select v-if="field.type === 'select'" v-model="form[field.key]" style="width:100%">
            <el-option v-for="option in field.options" :key="option" :label="option" :value="option" />
          </el-select>
          <el-select v-else-if="field.type === 'multi-select'" v-model="form[field.key]" multiple clearable collapse-tags collapse-tags-tooltip style="width:100%" placeholder="涓嶉€夊垯鎸夎鑹查粯璁ゆ樉绀鸿彍鍗?>
            <el-option v-for="option in field.options" :key="option" :label="permissionLabelMap[option] || option" :value="option" />
          </el-select>
          <el-input-number v-else-if="field.type === 'number'" v-model="form[field.key]" :min="0" :precision="field.key === 'stock' ? 0 : 2" controls-position="right" style="width:100%" />
          <el-date-picker v-else-if="field.type === 'date'" v-model="form[field.key]" value-format="YYYY-MM-DD" type="date" placeholder="璇烽€夋嫨鏃ユ湡" style="width:100%" />
          <el-switch v-else-if="field.type === 'switch'" v-model="form[field.key]" active-text="鍚敤" inactive-text="鍏抽棴" />
          <el-input v-else v-model="form[field.key]" :type="field.type === 'textarea' ? 'textarea' : field.type === 'password' ? 'password' : 'text'" :rows="3" :placeholder="field.placeholder || (field.key === 'login_password' ? '鏂板憳宸ラ粯璁ゅ彲濉?123456锛涚紪杈戞椂鐣欑┖琛ㄧず涓嶆敼瀵嗙爜' : `璇疯緭鍏?{field.label}`)" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">鍙栨秷</el-button>
        <el-button type="success" :loading="saving" @click="save">淇濆瓨</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="areaDialogVisible" title="鍖哄煙璁剧疆" width="720px" destroy-on-close>
      <el-form label-position="top" class="crud-form">
        <el-form-item label="鍖哄煙鍚嶇О" required>
          <el-input v-model="areaForm.area" placeholder="渚嬪锛欰鍖? />
        </el-form-item>
        <el-form-item label="璐熻矗涓荤">
          <el-select v-model="areaForm.supervisor_name" filterable allow-create clearable style="width:100%" placeholder="閫夋嫨鎴栬緭鍏ヤ富绠? @change="handleAreaSupervisorChange">
            <el-option v-for="employee in supervisorOptions" :key="employee.id" :label="employee.name" :value="employee.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="涓荤鐢佃瘽">
          <el-input v-model="areaForm.supervisor_phone" />
        </el-form-item>
        <el-form-item label="鐘舵€?>
          <el-select v-model="areaForm.status" style="width:100%">
            <el-option label="鍚敤" value="鍚敤" />
            <el-option label="鍋滅敤" value="鍋滅敤" />
          </el-select>
        </el-form-item>
      </el-form>
      <div style="display:flex;justify-content:center;gap:8px;margin-bottom:12px;">
        <el-button @click="resetAreaForm()">娓呯┖</el-button>
        <el-button type="success" @click="saveAreaSetting">{{ areaEditingId ? '淇濆瓨淇敼' : '鏂板鍖哄煙' }}</el-button>
      </div>
      <el-table :data="areaSettings" stripe empty-text="鏆傛棤鍖哄煙璁剧疆">
        <el-table-column prop="area" label="鍖哄煙" />
        <el-table-column prop="supervisor_name" label="涓荤" />
        <el-table-column prop="supervisor_phone" label="涓荤鐢佃瘽" />
        <el-table-column prop="status" label="鐘舵€? width="90" />
        <el-table-column label="鎿嶄綔" width="95">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="resetAreaForm(scope.row)">缂栬緫</el-dropdown-item>
                  <el-dropdown-item divided @click="removeAreaSetting(scope.row)">鍒犻櫎</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="areaDialogVisible=false">鍏抽棴</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.customer-crud-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.customer-crud-form .full {
  grid-column: 1 / -1;
}

</style>

