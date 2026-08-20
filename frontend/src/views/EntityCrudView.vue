<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

type EntityKind = 'customer' | 'employee'
type FieldType = 'text' | 'select' | 'multi-select' | 'date' | 'textarea' | 'switch' | 'password'
type Row = Record<string, any>

interface FieldConfig {
  key: string
  label: string
  type?: FieldType
  required?: boolean
  options?: string[]
  default?: string | boolean | string[]
  table?: boolean
  width?: number
  minWidth?: number
  placeholder?: string
}

interface EntityConfig {
  title: string
  eyebrow: string
  singular: string
  endpoint: string
  description: string
  fields: FieldConfig[]
}

const modulePermissionOptions = [
  { label: '首页工作台', value: 'dashboard' },
  { label: '商品管理', value: 'goods' },
  { label: '订单管理', value: 'orders' },
  { label: '客户管理', value: 'customers' },
  { label: '项目管理', value: 'projects' },
  { label: '采购仓管', value: 'purchase_inventory' },
  { label: '财务合同', value: 'finance' },
  { label: '报表分析', value: 'reports' },
  { label: '员工管理', value: 'staff' },
  { label: '车辆管理', value: 'vehicle' },
  { label: '配送养护', value: 'schedule_workflow' },
  { label: '系统设置', value: 'system' },
]

const customerTypeOptions = ['项目客户', '企业客户', '个人业务']
const statusOptions = ['启用', '停用']
const employeeStatusOptions = ['在职', '停用', '离职']
const defaultPositions = ['经理', '主管', '客服', '养护员', '司机', '跟车配送', '采购', '仓管', '财务', '市场']
const defaultDepartments = ['市场部', '绿化部', '财务部', '采购部', '仓管部', '配送部', '客服部', '管理层', '其他']

const configs: Record<EntityKind, EntityConfig> = {
  customer: {
    title: '客户管理',
    eyebrow: 'CUSTOMERS',
    singular: '客户',
    endpoint: '/customers',
    description: '维护客户、项目名称、联系人、区域主管和养护员信息，方便订单自动带出联系信息。',
    fields: [
      { key: 'customer_type', label: '客户类型', type: 'select', options: customerTypeOptions, default: '项目客户', required: true, table: true, width: 110 },
      { key: 'name', label: '客户名称', required: true, table: true, minWidth: 160 },
      { key: 'project_name', label: '项目名称', table: true, minWidth: 170 },
      { key: 'contact_person', label: '负责人', table: true, width: 110 },
      { key: 'phone', label: '负责人电话', table: true, width: 130 },
      { key: 'address', label: '地址', type: 'textarea', table: true, minWidth: 220 },
      { key: 'area', label: '区域', table: true, width: 100 },
      { key: 'supervisor_name', label: '主管', table: true, width: 110 },
      { key: 'supervisor_phone', label: '主管电话', table: true, width: 130 },
      { key: 'maintainer_name', label: '养护员', table: true, width: 110 },
      { key: 'maintainer_phone', label: '养护员电话', table: true, width: 130 },
      { key: 'status', label: '状态', type: 'select', options: statusOptions, default: '启用', table: true, width: 90 },
    ],
  },
  employee: {
    title: '员工管理',
    eyebrow: 'EMPLOYEES',
    singular: '员工',
    endpoint: '/employees',
    description: '维护员工档案、手机号登录账号、岗位部门、模块权限和商品分类权限。',
    fields: [
      { key: 'name', label: '姓名', required: true, table: true, width: 110 },
      { key: 'phone', label: '手机号/账号', table: true, width: 140 },
      { key: 'department', label: '部门', type: 'select', options: defaultDepartments, table: true, width: 110 },
      { key: 'position', label: '岗位', type: 'select', options: defaultPositions, table: true, width: 120 },
      { key: 'hire_date', label: '入职日期', type: 'date', table: true, width: 120 },
      { key: 'leave_date', label: '离职日期', type: 'date', table: false },
      { key: 'login_enabled', label: '允许登录', type: 'switch', default: false, table: true, width: 100 },
      { key: 'login_password', label: '登录密码', type: 'password', table: false, placeholder: '新员工默认可填；编辑时留空不修改密码' },
      { key: 'module_permissions', label: '模块权限', type: 'multi-select', options: modulePermissionOptions.map((item) => item.value), table: false },
      { key: 'product_category_permissions', label: '商品分类权限', type: 'multi-select', options: [], table: false },
      { key: 'responsibility', label: '负责项目/说明', type: 'textarea', table: false },
      { key: 'status', label: '状态', type: 'select', options: employeeStatusOptions, default: '在职', table: true, width: 90 },
    ],
  },
}

const route = useRoute()
const entity = computed(() => (route.meta.entity || 'customer') as EntityKind)
const config = computed(() => configs[entity.value])
const tableFields = computed(() => config.value.fields.filter((field) => field.table !== false))
const visibleFormFields = computed(() => {
  return config.value.fields.filter((field) => {
    if (entity.value === 'customer' && field.key === 'project_name') return form.customer_type !== '个人业务'
    return true
  })
})

const rows = ref<Row[]>([])
const employees = ref<Row[]>([])
const areaSettings = ref<Row[]>([])
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const areaDialogVisible = ref(false)
const editingId = ref<number | null>(null)
const areaEditingId = ref<number | null>(null)
const form = reactive<Row>({})
const areaForm = reactive<Row>({ area: '', supervisor_name: '', supervisor_phone: '', status: '启用' })

const supervisorOptions = computed(() => employees.value.filter((item) => `${item.position},${item.role}`.includes('主管') || `${item.position},${item.role}`.includes('经理')))
const maintainerOptions = computed(() => employees.value.filter((item) => `${item.position},${item.role}`.includes('养护')))
const areaOptions = computed(() => areaSettings.value.map((item) => item.area).filter(Boolean))

function fieldOptions(field: FieldConfig) {
  if (field.key === 'area') return areaOptions.value
  if (field.key === 'supervisor_name') return supervisorOptions.value.map((item) => item.name)
  if (field.key === 'maintainer_name') return maintainerOptions.value.map((item) => item.name)
  if (field.key === 'module_permissions') return modulePermissionOptions.map((item) => item.value)
  return field.options || []
}

function optionLabel(field: FieldConfig, value: string) {
  if (field.key === 'module_permissions') {
    return modulePermissionOptions.find((item) => item.value === value)?.label || value
  }
  return value
}

function splitValue(value: unknown) {
  if (Array.isArray(value)) return value
  return String(value || '').replace(/，/g, ',').split(',').map((item) => item.trim()).filter(Boolean)
}

function displayValue(row: Row, field: FieldConfig) {
  const value = row[field.key]
  if (field.type === 'switch') return value ? '是' : '否'
  if (field.type === 'multi-select') return splitValue(value).map((item) => optionLabel(field, item)).join('、')
  if (entity.value === 'customer' && field.key === 'project_name' && row.customer_type === '个人业务') return '-'
  return value || '-'
}

function resetForm(row?: Row) {
  Object.keys(form).forEach((key) => delete form[key])
  config.value.fields.forEach((field) => {
    if (field.type === 'multi-select') form[field.key] = row ? splitValue(row[field.key]) : []
    else if (field.type === 'switch') form[field.key] = row ? Boolean(row[field.key]) : Boolean(field.default)
    else if (field.key === 'login_password') form[field.key] = ''
    else form[field.key] = row ? (row[field.key] ?? '') : (field.default ?? '')
  })
}

async function loadRows() {
  loading.value = true
  try {
    const response = await api.get(config.value.endpoint, { params: { keyword: keyword.value.trim() } })
    rows.value = response.data.items || []
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '数据加载失败')
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
    const categories = (await api.get('/products/categories')).data.items || []
    const field = configs.employee.fields.find((item) => item.key === 'product_category_permissions')
    if (field) field.options = categories
  } catch {
    const field = configs.employee.fields.find((item) => item.key === 'product_category_permissions')
    if (field) field.options = []
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

async function removeRow(row: Row) {
  await ElMessageBox.confirm(`确定删除“${row.name || row.phone || row.id}”吗？`, '删除确认', { type: 'warning' })
  await api.delete(`${config.value.endpoint}/${row.id}`)
  ElMessage.success('删除成功')
  await loadRows()
}

function normalizePayload() {
  const payload: Row = { ...form }
  config.value.fields.filter((field) => field.type === 'multi-select').forEach((field) => {
    payload[field.key] = Array.isArray(payload[field.key]) ? payload[field.key].join(',') : ''
  })
  if (entity.value === 'customer' && payload.customer_type === '个人业务') payload.project_name = ''
  if (!payload.login_password) delete payload.login_password
  return payload
}

async function saveRow() {
  const required = config.value.fields.find((field) => field.required && !String(form[field.key] || '').trim())
  if (required) {
    ElMessage.warning(`请填写${required.label}`)
    return
  }
  saving.value = true
  try {
    const payload = normalizePayload()
    if (editingId.value) await api.put(`${config.value.endpoint}/${editingId.value}`, payload)
    else await api.post(config.value.endpoint, payload)
    ElMessage.success(editingId.value ? '修改成功' : '新增成功')
    dialogVisible.value = false
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function handleAreaChange(area: string) {
  const setting = areaSettings.value.find((item) => item.area === area)
  if (!setting) return
  form.supervisor_name = setting.supervisor_name || ''
  form.supervisor_phone = setting.supervisor_phone || ''
}

function handlePersonChange(field: string, name: string) {
  const employee = employees.value.find((item) => item.name === name)
  if (!employee) return
  if (field === 'supervisor_name') form.supervisor_phone = employee.phone || ''
  if (field === 'maintainer_name') form.maintainer_phone = employee.phone || ''
  if (field === 'area_supervisor') areaForm.supervisor_phone = employee.phone || ''
}

function resetAreaForm(row?: Row) {
  areaEditingId.value = row?.id ? Number(row.id) : null
  areaForm.area = row?.area || ''
  areaForm.supervisor_name = row?.supervisor_name || ''
  areaForm.supervisor_phone = row?.supervisor_phone || ''
  areaForm.status = row?.status || '启用'
}

function openAreaDialog() {
  resetAreaForm()
  areaDialogVisible.value = true
}

async function saveAreaSetting() {
  if (!String(areaForm.area || '').trim()) {
    ElMessage.warning('请填写区域')
    return
  }
  try {
    const payload = { ...areaForm, area: String(areaForm.area).trim() }
    if (areaEditingId.value) await api.put(`/customers/area-settings/${areaEditingId.value}`, payload)
    else await api.post('/customers/area-settings', payload)
    ElMessage.success(areaEditingId.value ? '区域修改成功' : '区域新增成功')
    resetAreaForm()
    await loadAreaSettings()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '区域保存失败')
  }
}

async function removeAreaSetting(row: Row) {
  await ElMessageBox.confirm(`确定删除区域“${row.area}”吗？`, '删除确认', { type: 'warning' })
  await api.delete(`/customers/area-settings/${row.id}`)
  ElMessage.success('区域删除成功')
  await loadAreaSettings()
}

function fieldSpan(field: FieldConfig) {
  if (field.type === 'textarea' || field.type === 'multi-select') return 2
  if (entity.value === 'customer' && field.key === 'customer_type' && form.customer_type !== '个人业务') return 2
  return 1
}

watch(entity, async () => {
  keyword.value = ''
  resetForm()
  await Promise.all([loadRows(), loadEmployees(), loadAreaSettings(), loadProductCategories()])
}, { immediate: true })
</script>

<template>
  <section class="crud-page">
    <div class="page-head">
      <div>
        <p class="eyebrow">{{ config.eyebrow }}</p>
        <h1>{{ config.title }}</h1>
        <p>{{ config.description }}</p>
      </div>
      <div class="head-actions">
        <el-button v-if="entity === 'customer'" plain type="success" @click="openAreaDialog">区域设置</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增{{ config.singular }}</el-button>
      </div>
    </div>

    <div class="table-card">
      <div class="toolbar">
        <el-input v-model="keyword" class="search-input" clearable placeholder="输入关键词搜索" :prefix-icon="Search" @keyup.enter="loadRows" />
        <el-button type="success" plain :icon="Search" @click="loadRows">查询</el-button>
        <el-button :icon="Refresh" @click="keyword = ''; loadRows()">重置</el-button>
        <span class="total">共 {{ rows.length }} 条</span>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe class="data-table" empty-text="暂无数据">
        <el-table-column v-for="field in tableFields" :key="field.key" :prop="field.key" :label="field.label" :width="field.width" :min-width="field.minWidth">
          <template #default="{ row }">
            <span>{{ displayValue(row, field) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="128">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Edit" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" :icon="Delete" @click="removeRow(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="`${editingId ? '编辑' : '新增'}${config.singular}`" width="780px" destroy-on-close align-center>
      <el-form label-position="top" class="crud-form">
        <el-form-item v-for="field in visibleFormFields" :key="field.key" :label="field.label" :class="{ wide: fieldSpan(field) === 2 }">
          <el-select
            v-if="field.type === 'select' && ['area', 'supervisor_name', 'maintainer_name'].includes(field.key)"
            v-model="form[field.key]"
            filterable
            allow-create
            clearable
            style="width:100%"
            :placeholder="field.placeholder || `请选择${field.label}`"
            @change="field.key === 'area' ? handleAreaChange($event) : handlePersonChange(field.key, $event)"
          >
            <el-option v-for="option in fieldOptions(field)" :key="option" :label="option" :value="option" />
          </el-select>

          <el-select
            v-else-if="field.type === 'select'"
            v-model="form[field.key]"
            filterable
            allow-create
            clearable
            style="width:100%"
            :placeholder="field.placeholder || `请选择${field.label}`"
          >
            <el-option v-for="option in fieldOptions(field)" :key="option" :label="option" :value="option" />
          </el-select>

          <el-select
            v-else-if="field.type === 'multi-select'"
            v-model="form[field.key]"
            multiple
            filterable
            clearable
            collapse-tags
            collapse-tags-tooltip
            style="width:100%"
            :placeholder="field.placeholder || `请选择${field.label}`"
          >
            <el-option v-for="option in fieldOptions(field)" :key="option" :label="optionLabel(field, option)" :value="option" />
          </el-select>

          <el-date-picker v-else-if="field.type === 'date'" v-model="form[field.key]" type="date" value-format="YYYY-MM-DD" format="YYYY年MM月DD日" placeholder="选择日期" style="width:100%" />
          <el-switch v-else-if="field.type === 'switch'" v-model="form[field.key]" />
          <el-input v-else-if="field.type === 'textarea'" v-model="form[field.key]" type="textarea" :rows="3" :placeholder="field.placeholder || `请输入${field.label}`" />
          <el-input v-else-if="field.type === 'password'" v-model="form[field.key]" type="password" show-password :placeholder="field.placeholder || `请输入${field.label}`" />
          <el-input v-else v-model="form[field.key]" :placeholder="field.placeholder || `请输入${field.label}`" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveRow">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="areaDialogVisible" title="区域设置" width="760px" destroy-on-close align-center>
      <el-form label-position="top" class="area-form">
        <el-form-item label="区域">
          <el-input v-model="areaForm.area" placeholder="例如：A区" />
        </el-form-item>
        <el-form-item label="主管名称">
          <el-select v-model="areaForm.supervisor_name" filterable allow-create clearable style="width:100%" placeholder="选择或输入主管" @change="handlePersonChange('area_supervisor', $event)">
            <el-option v-for="employee in supervisorOptions" :key="employee.id" :label="employee.name" :value="employee.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="主管电话">
          <el-input v-model="areaForm.supervisor_phone" placeholder="主管电话" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="areaForm.status" style="width:100%">
            <el-option v-for="item in statusOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
      </el-form>
      <div class="area-actions">
        <el-button type="primary" @click="saveAreaSetting">{{ areaEditingId ? '保存区域' : '新增区域' }}</el-button>
        <el-button @click="resetAreaForm()">清空</el-button>
      </div>
      <el-table :data="areaSettings" border size="small" empty-text="暂无区域">
        <el-table-column prop="area" label="区域" width="120" />
        <el-table-column prop="supervisor_name" label="主管" />
        <el-table-column prop="supervisor_phone" label="主管电话" />
        <el-table-column prop="status" label="状态" width="90" />
        <el-table-column label="操作" width="130">
          <template #default="{ row }">
            <el-button link type="primary" @click="resetAreaForm(row)">编辑</el-button>
            <el-button link type="danger" @click="removeAreaSetting(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </section>
</template>

<style scoped>
.crud-page {
  display: grid;
  gap: 18px;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.eyebrow {
  margin: 0 0 4px;
  color: #2f7df6;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .08em;
}

.page-head h1 {
  margin: 0;
  color: #14314d;
  font-size: 24px;
}

.page-head p {
  margin: 6px 0 0;
  color: #6f8192;
}

.head-actions,
.toolbar,
.area-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.table-card {
  padding: 16px;
  border: 1px solid #d7ecff;
  border-radius: 18px;
  background: rgba(255, 255, 255, .86);
  box-shadow: 0 16px 35px rgba(33, 106, 178, .08);
}

.toolbar {
  margin-bottom: 14px;
}

.search-input {
  width: 260px;
}

.total {
  color: #60798f;
}

.data-table {
  width: 100%;
}

.crud-form,
.area-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2px 18px;
}

.crud-form .wide {
  grid-column: 1 / -1;
}

.area-actions {
  justify-content: center;
  margin: 0 0 14px;
}

:deep(.el-dialog) {
  border-radius: 20px;
}

:deep(.el-table th.el-table__cell) {
  background: #f3f9ff;
  color: #29445d;
}
</style>
