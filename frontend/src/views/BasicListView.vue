<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>
type Column = { prop: string; label: string; width?: number; minWidth?: number }
type FieldType = 'text' | 'number' | 'select' | 'multi-select' | 'date' | 'textarea' | 'switch' | 'password' | 'file'
type OptionItem = { label: string; value: any }
type Field = {
  key: string
  label: string
  type?: FieldType
  required?: boolean
  default?: any
  options?: OptionItem[] | string[]
  optionEndpoint?: string
  optionLabel?: string
  optionValue?: string
  placeholder?: string
  createOnly?: boolean
  editOnly?: boolean
  readonly?: boolean
  full?: boolean
}
type RowAction = {
  label: string
  type?: 'primary' | 'success' | 'warning' | 'danger' | 'info'
  endpoint: string
  method?: 'post' | 'put' | 'delete'
  confirm?: string
  payload?: Row
}

const route = useRoute()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const rows = ref<Row[]>([])
const total = ref(0)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<Row>({})
const optionMap = reactive<Record<string, OptionItem[]>>({})

const pageTitle = computed(() => String(route.meta.title || '数据管理'))
const endpoint = computed(() => String(route.meta.endpoint || ''))
const createEndpoint = computed(() => String(route.meta.createEndpoint || endpoint.value))
const updateEndpoint = computed(() => String(route.meta.updateEndpoint || endpoint.value))
const deleteEndpoint = computed(() => String(route.meta.deleteEndpoint || endpoint.value))
const idKey = computed(() => String(route.meta.idKey || 'id'))
const canCreate = computed(() => Boolean(route.meta.canCreate && formFields.value.length))
const canEdit = computed(() => Boolean(route.meta.canEdit && formFields.value.length))
const canDelete = computed(() => Boolean(route.meta.canDelete))
const columns = computed<Column[]>(() => Array.isArray(route.meta.columns) ? route.meta.columns as Column[] : [])
const formFields = computed<Field[]>(() => Array.isArray(route.meta.formFields) ? route.meta.formFields as Field[] : [])
const rowActions = computed<RowAction[]>(() => Array.isArray(route.meta.rowActions) ? route.meta.rowActions as RowAction[] : [])

function valueText(row: Row, prop: string) {
  const value = row[prop]
  if (value === null || value === undefined || value === '') return '-'
  if (Array.isArray(value)) return value.join('、')
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(2)))
  return String(value)
}

function replacePath(template: string, row: Row) {
  return template.replace(/\{(\w+)\}/g, (_, key) => encodeURIComponent(String(row[key] ?? '')))
}

function normalizeOptions(field: Field): OptionItem[] {
  const values = optionMap[field.key] || field.options || []
  return values.map((item: any) => typeof item === 'string' ? { label: item, value: item } : item)
}

async function loadOptions() {
  const fields = formFields.value.filter((field) => field.optionEndpoint)
  await Promise.all(fields.map(async (field) => {
    try {
      const response = await api.get(String(field.optionEndpoint))
      const items = Array.isArray(response.data) ? response.data : response.data.items || []
      optionMap[field.key] = items.map((item: Row) => ({
        label: String(item[field.optionLabel || 'name'] ?? item.name ?? item.label ?? item.id),
        value: item[field.optionValue || 'id'] ?? item.value ?? item.id,
      }))
    } catch {
      optionMap[field.key] = []
    }
  }))
}

async function loadRows() {
  if (!endpoint.value) return
  loading.value = true
  try {
    const response = await api.get(endpoint.value, { params: { keyword: keyword.value.trim() || undefined } })
    const data = response.data
    rows.value = Array.isArray(data) ? data : data.items || []
    total.value = Number(data.total ?? rows.value.length)
  } catch (error: any) {
    rows.value = []
    total.value = 0
    ElMessage.error(error.response?.data?.detail || `${pageTitle.value}加载失败`)
  } finally {
    loading.value = false
  }
}

function resetSearch() {
  keyword.value = ''
  loadRows()
}

function resetForm(row?: Row) {
  Object.keys(form).forEach((key) => delete form[key])
  formFields.value.forEach((field) => {
    if (field.editOnly && !row) return
    if (field.createOnly && row) return
    if (field.type === 'multi-select') {
      const raw = row ? row[field.key] : field.default
      form[field.key] = Array.isArray(raw) ? raw : String(raw || '').split(',').map((item) => item.trim()).filter(Boolean)
    } else if (field.type === 'switch') {
      form[field.key] = row ? Boolean(row[field.key]) : Boolean(field.default)
    } else if (field.key === 'password' && row) {
      form[field.key] = ''
    } else {
      form[field.key] = row ? (row[field.key] ?? '') : (field.default ?? '')
    }
  })
}

function openCreate() {
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEdit(row: Row) {
  editingId.value = Number(row[idKey.value])
  resetForm(row)
  dialogVisible.value = true
}

function normalizePayload() {
  const payload: Row = {}
  formFields.value.forEach((field) => {
    if (field.readonly) return
    if (field.editOnly && !editingId.value) return
    if (field.createOnly && editingId.value) return
    const value = form[field.key]
    if (field.type === 'multi-select') payload[field.key] = Array.isArray(value) ? value.join(',') : ''
    else if (field.type === 'number') payload[field.key] = value === '' || value === null || value === undefined ? 0 : Number(value)
    else if (field.type === 'switch') payload[field.key] = Boolean(value)
    else if (field.type === 'password' && !value) return
    else payload[field.key] = value
  })
  return payload
}

async function saveRow() {
  const required = formFields.value.find((field) => field.required && !String(form[field.key] ?? '').trim())
  if (required) {
    ElMessage.warning(`请填写${required.label}`)
    return
  }
  saving.value = true
  try {
    const payload = normalizePayload()
    if (editingId.value) await api.put(`${updateEndpoint.value}/${editingId.value}`, payload)
    else await api.post(createEndpoint.value, payload)
    ElMessage.success(editingId.value ? '修改成功' : '新增成功')
    dialogVisible.value = false
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function removeRow(row: Row) {
  await ElMessageBox.confirm(`确定删除这条${pageTitle.value}记录吗？`, '删除确认', { type: 'warning' })
  await api.delete(`${deleteEndpoint.value}/${row[idKey.value]}`)
  ElMessage.success('删除成功')
  await loadRows()
}

async function runAction(action: RowAction, row: Row) {
  if (action.confirm) await ElMessageBox.confirm(action.confirm, '操作确认', { type: 'warning' })
  try {
    const url = replacePath(action.endpoint, row)
    const method = action.method || 'post'
    if (method === 'delete') await api.delete(url)
    else if (method === 'put') await api.put(url, action.payload || {})
    else await api.post(url, action.payload || {})
    ElMessage.success(`${action.label}成功`)
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || `${action.label}失败`)
  }
}

function handleFile(field: Field, file: File) {
  const reader = new FileReader()
  reader.onload = () => {
    form[field.key] = String(reader.result || '')
    if (!form.file_name) form.file_name = file.name
    if (!form.file_size) form.file_size = file.size
  }
  reader.readAsDataURL(file)
  return false
}

function beforeUpload(field: Field) {
  return (file: File) => handleFile(field, file)
}

async function reload() {
  await loadOptions()
  await loadRows()
}

watch(() => route.fullPath, reload)
onMounted(reload)
</script>

<template>
  <div class="page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">BUSINESS DATA</p>
        <h1>{{ pageTitle }}</h1>
        <p>支持查询、新增、编辑、删除和常用业务操作，数据直接对接后台接口。</p>
      </div>
      <el-button v-if="canCreate" type="primary" :icon="Plus" @click="openCreate">新增{{ pageTitle }}</el-button>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar">
        <el-input
          v-model="keyword"
          clearable
          :prefix-icon="Search"
          placeholder="输入关键词搜索"
          @keyup.enter="loadRows"
          @clear="loadRows"
        />
        <el-button type="success" plain :icon="Search" @click="loadRows">查询</el-button>
        <el-button :icon="Refresh" @click="resetSearch">重置</el-button>
        <span class="table-count">共 {{ total }} 条</span>
      </div>

      <el-table v-loading="loading" :data="rows" stripe border empty-text="暂无数据">
        <el-table-column
          v-for="column in columns"
          :key="column.prop"
          :prop="column.prop"
          :label="column.label"
          :width="column.width"
          :min-width="column.minWidth || 120"
          show-overflow-tooltip
        >
          <template #default="scope">{{ valueText(scope.row, column.prop) }}</template>
        </el-table-column>
        <el-table-column v-if="canEdit || canDelete || rowActions.length" label="操作" fixed="right" width="160">
          <template #default="{ row }">
            <el-dropdown trigger="click">
              <el-button link type="primary">更多</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-if="canEdit" :icon="Edit" @click="openEdit(row)">编辑</el-dropdown-item>
                  <el-dropdown-item v-for="action in rowActions" :key="action.label" @click="runAction(action, row)">
                    {{ action.label }}
                  </el-dropdown-item>
                  <el-dropdown-item v-if="canDelete" divided :icon="Delete" @click="removeRow(row)">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <el-dialog v-model="dialogVisible" :title="`${editingId ? '编辑' : '新增'}${pageTitle}`" width="780px" destroy-on-close align-center>
      <el-form label-position="top" class="crud-form">
        <el-form-item
          v-for="field in formFields.filter((item) => !(item.editOnly && !editingId) && !(item.createOnly && editingId))"
          :key="field.key"
          :label="field.label"
          :class="{ wide: field.full || field.type === 'textarea' || field.type === 'multi-select' || field.type === 'file' }"
        >
          <el-input v-if="!field.type || field.type === 'text'" v-model="form[field.key]" :disabled="field.readonly" :placeholder="field.placeholder || `请输入${field.label}`" />
          <el-input-number v-else-if="field.type === 'number'" v-model="form[field.key]" :min="0" :controls="false" style="width:100%" />
          <el-select v-else-if="field.type === 'select'" v-model="form[field.key]" filterable clearable style="width:100%" :placeholder="field.placeholder || `请选择${field.label}`">
            <el-option v-for="option in normalizeOptions(field)" :key="String(option.value)" :label="option.label" :value="option.value" />
          </el-select>
          <el-select v-else-if="field.type === 'multi-select'" v-model="form[field.key]" multiple filterable clearable collapse-tags collapse-tags-tooltip style="width:100%" :placeholder="field.placeholder || `请选择${field.label}`">
            <el-option v-for="option in normalizeOptions(field)" :key="String(option.value)" :label="option.label" :value="option.value" />
          </el-select>
          <el-date-picker v-else-if="field.type === 'date'" v-model="form[field.key]" type="date" value-format="YYYY-MM-DD" format="YYYY年MM月DD日" placeholder="选择日期" style="width:100%" />
          <el-switch v-else-if="field.type === 'switch'" v-model="form[field.key]" />
          <el-input v-else-if="field.type === 'textarea'" v-model="form[field.key]" type="textarea" :rows="3" :placeholder="field.placeholder || `请输入${field.label}`" />
          <el-input v-else-if="field.type === 'password'" v-model="form[field.key]" type="password" show-password :placeholder="field.placeholder || `请输入${field.label}`" />
          <el-upload v-else-if="field.type === 'file'" drag action="#" :auto-upload="false" :show-file-list="false" :before-upload="beforeUpload(field)">
            <div class="upload-text">{{ form[field.key] ? '已选择文件，可重新选择' : '拖入或点击选择文件' }}</div>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveRow">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.table-panel {
  overflow: hidden;
}

.table-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.table-toolbar .el-input {
  width: 260px;
}

.table-count {
  color: #6f8192;
}

.crud-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2px 18px;
}

.crud-form .wide {
  grid-column: 1 / -1;
}

.upload-text {
  color: #60798f;
  font-size: 14px;
}

:deep(.el-table th.el-table__cell) {
  background: #f3f9ff;
  color: #29445d;
}

:deep(.el-dialog) {
  border-radius: 20px;
}
</style>
