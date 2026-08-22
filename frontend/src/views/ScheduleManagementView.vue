<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDown, Check, Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const route = useRoute()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const today = new Date().toISOString().slice(0, 10)
const selectedDate = ref(today)
const vehicleKeyword = ref('')
const employeeFilter = ref('')
const scheduleStatus = ref('待完成')
const dateRange = ref<[string, string] | null>(null)
const rows = ref<Row[]>([])
const employees = ref<Row[]>([])
const vehicles = ref<Row[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<Row>({})

const statusOptions = ['待完成', '待发布', '已发布', '配送中', '已出发', '已送达', '已完成', '已取消']

const filteredRows = computed(() => {
  const plate = vehicleKeyword.value.trim().toLowerCase()
  const employee = String(employeeFilter.value || '')
  const range = dateRange.value
  return rows.value.filter((row) => {
    const rowDate = row.schedule_date || ''
    const matchDate = !range?.length || (rowDate >= range[0] && rowDate <= range[1])
    const matchPlate = !plate || String(row.vehicle_plate_no || '').toLowerCase().includes(plate)
    const assistantIds = normalizeAssistantIds(row.assistant_ids).map(String)
    const matchEmployee = !employee
      || String(row.driver_id || '') === employee
      || assistantIds.includes(employee)
      || String(row.driver_name || '').includes(employee)
      || String(row.assistant_names || '').includes(employee)
    const matchStatus = !scheduleStatus.value
      || (scheduleStatus.value === '待完成' ? !['已完成', '已取消'].includes(row.status) : row.status === scheduleStatus.value)
    return matchDate && matchPlate && matchEmployee && matchStatus
  })
})

const scheduleSheetRows = computed<(Row & { dateRowspan: number; crewRowspan: number; plantLines: string[] })[]>(() => {
  const sorted = [...filteredRows.value].sort((a, b) => {
    const dateCompare = String(a.schedule_date || '').localeCompare(String(b.schedule_date || ''))
    if (dateCompare) return dateCompare
    const driverCompare = String(a.driver_name || '').localeCompare(String(b.driver_name || ''))
    if (driverCompare) return driverCompare
    const assistantCompare = String(a.assistant_names || '').localeCompare(String(b.assistant_names || ''))
    if (assistantCompare) return assistantCompare
    return String(a.vehicle_plate_no || '').localeCompare(String(b.vehicle_plate_no || ''))
  })
  return sorted.map((row, index) => {
    const previous = sorted[index - 1]
    const sameDateRows = sorted.filter((item) => item.schedule_date === row.schedule_date).length
    const currentCrewKey = crewMergeKey(row)
    const previousCrewKey = previous ? crewMergeKey(previous) : ''
    const sameCrewRows = sorted.filter((item) => crewMergeKey(item) === currentCrewKey).length
    return {
      ...row,
      dateRowspan: previous?.schedule_date === row.schedule_date ? 0 : sameDateRows,
      crewRowspan: previousCrewKey === currentCrewKey ? 0 : sameCrewRows,
      plantLines: plantDetailLines(row),
    }
  })
})

const taskCount = computed(() => filteredRows.value.length)
const publishedCount = computed(() => filteredRows.value.filter((row) => ['已发布', '已出发', '配送中', '已送达', '已完成'].includes(row.status)).length)
const doneCount = computed(() => filteredRows.value.filter((row) => row.status === '已完成').length)

function resetForm(values: Row) {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, values)
}

function emptyTask() {
  return {
    task_no: `RC-${Date.now().toString().slice(-8)}`,
    schedule_date: selectedDate.value,
    task_type: '配送',
    source_type: '手工',
    source_no: '',
    project_name: '',
    address: '',
    driver_id: null,
    assistant_ids: [] as number[],
    vehicle_id: null,
    planned_start: '',
    planned_end: '',
    item_summary: '',
    status: '待发布',
    notes: '',
  }
}

function statusTag(status: string) {
  if (status === '已完成') return 'success'
  if (status === '已取消') return 'info'
  if (status === '配送中' || status === '已出发') return 'warning'
  if (status === '已送达') return 'success'
  if (status === '已发布') return 'primary'
  return ''
}

function normalizeAssistantIds(value: string | number[] | null | undefined) {
  if (Array.isArray(value)) return value.map(Number).filter(Boolean)
  return String(value || '').split(',').map((item) => Number(item.trim())).filter(Boolean)
}

function formatTime(row: Row) {
  return [row.planned_start, row.planned_end].filter(Boolean).join(' - ') || '未定'
}

function crewMergeKey(row: Row) {
  return [
    row.schedule_date || '',
    row.vehicle_plate_no || '',
    row.driver_id || row.driver_name || '',
    normalizeAssistantIds(row.assistant_ids).join(',') || row.assistant_names || '',
  ].join('|')
}

function resetFilters() {
  vehicleKeyword.value = ''
  employeeFilter.value = ''
  scheduleStatus.value = '待完成'
  dateRange.value = null
  loadRows()
}

function applyRouteDate() {
  const date = String(route.query.date || '').trim()
  if (!date) return
  selectedDate.value = date
  dateRange.value = [date, date]
}

function plantDetailLines(row: Row) {
  const raw = String(row.item_summary || '').trim()
  if (!raw) return ['暂无植物明细']
  return raw
    .replaceAll('×', ' ')
    .replaceAll('脳', ' ')
    .split(/[;；\n]/)
    .map((item) => item.replace(/\s+/g, ' ').trim())
    .filter(Boolean)
}

async function loadOptions() {
  const [employeeResponse, vehicleResponse] = await Promise.all([
    api.get('/employees'),
    api.get('/vehicles'),
  ])
  employees.value = employeeResponse.data.items
  vehicles.value = vehicleResponse.data.items
}

async function loadRows() {
  loading.value = true
  try {
    rows.value = (await api.get('/schedules', {
      params: { keyword: keyword.value.trim() || undefined },
    })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '日程安排加载失败')
  } finally {
    loading.value = false
  }
}

async function openCreate() {
  editingId.value = null
  await loadOptions()
  resetForm(emptyTask())
  dialogVisible.value = true
}

async function openEdit(row: Row) {
  editingId.value = row.id
  await loadOptions()
  resetForm({ ...row, schedule_date: row.schedule_date || selectedDate.value, assistant_ids: normalizeAssistantIds(row.assistant_ids) })
  dialogVisible.value = true
}

function validateForm() {
  if (!form.task_no?.trim()) { ElMessage.warning('请填写安排单号'); return false }
  if (!form.schedule_date) { ElMessage.warning('请选择安排日期'); return false }
  if (!form.project_name?.trim()) { ElMessage.warning('请填写项目/任务名称'); return false }
  if (!form.driver_id) { ElMessage.warning('请选择司机'); return false }
  if (!form.item_summary?.trim()) { ElMessage.warning('请填写植物清单或任务内容'); return false }
  return true
}

async function saveTask() {
  if (!validateForm()) return
  saving.value = true
  try {
    const payload = {
      ...form,
      task_no: form.task_no.trim(),
      project_name: form.project_name.trim(),
      schedule_date: form.schedule_date || null,
      assistant_ids: normalizeAssistantIds(form.assistant_ids).join(','),
      driver_id: form.driver_id || null,
      vehicle_id: form.vehicle_id || null,
    }
    if (editingId.value) await api.put(`/schedules/${editingId.value}`, payload)
    else await api.post('/schedules', payload)
    ElMessage.success(`安排已${editingId.value ? '修改' : '新增'}`)
    dialogVisible.value = false
    selectedDate.value = payload.schedule_date
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '日程安排保存失败')
  } finally {
    saving.value = false
  }
}

async function changeStatus(row: Row, status: string) {
  try {
    await api.post(`/schedules/${row.id}/status`, { status })
    ElMessage.success(`状态已改为${status}`)
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '状态修改失败')
  }
}

async function deleteTask(row: Row) {
  await ElMessageBox.confirm(`确认删除安排“${row.task_no}”吗？`, '删除安排', { type: 'warning' })
  try {
    await api.delete(`/schedules/${row.id}`)
    ElMessage.success('安排已删除')
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '安排删除失败')
  }
}

watch(() => route.query.date, () => {
  applyRouteDate()
})

applyRouteDate()
loadOptions()
loadRows()
</script>

<template>
  <div class="page schedule-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">SCHEDULE</p>
        <h1>每日安排表</h1>
        <p>客服可以把第二天配送、撤花、修剪打药等任务排出来；所有人看整体表，个人任务后面再细化。</p>
      </div>
      <el-button type="success" :icon="Plus" @click="openCreate">新增安排</el-button>
    </div>

    <div class="inventory-summary">
      <div><span>当日安排</span><strong>{{ taskCount }}</strong></div>
      <div><span>已发布/执行</span><strong>{{ publishedCount }}</strong></div>
      <div><span>已完成</span><strong>{{ doneCount }}</strong></div>
    </div>

    <article class="panel schedule-sheet-panel" v-loading="loading">
      <div class="schedule-filter-bar">
        <label>车牌号：</label>
        <el-input v-model="vehicleKeyword" clearable placeholder="请输入车牌号" />
        <label>员工：</label>
        <el-select v-model="employeeFilter" filterable clearable placeholder="点击选择员工">
          <el-option v-for="employee in employees" :key="employee.id" :label="`${employee.name} ${employee.position || ''}`" :value="String(employee.id)" />
        </el-select>
        <label>日程状态：</label>
        <el-select v-model="scheduleStatus" clearable placeholder="全部">
          <el-option v-for="status in statusOptions" :key="status" :label="status" :value="status" />
        </el-select>
        <label>派单时间：</label>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="到"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
        />
        <el-button type="primary" :icon="Search" @click="loadRows">筛选</el-button>
        <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
      </div>

      <div class="schedule-sheet-title">绿风环境花卉管理软件日程安排</div>

      <table class="schedule-sheet-table">
        <thead>
          <tr>
            <th>日期</th>
            <th>车辆</th>
            <th>送货人员</th>
            <th>跟车人员</th>
            <th>派单的项目</th>
            <th>植物明细</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!scheduleSheetRows.length">
            <td colspan="6" class="empty-cell">暂无符合条件的日程安排</td>
          </tr>
          <tr v-for="row in scheduleSheetRows" :key="row.id || row.task_no">
            <td v-if="row.dateRowspan" :rowspan="row.dateRowspan" class="schedule-date-cell">{{ row.schedule_date || '-' }}</td>
            <td v-if="row.crewRowspan" :rowspan="row.crewRowspan" class="schedule-merge-cell">{{ row.vehicle_plate_no || '未安排车辆' }}</td>
            <td v-if="row.crewRowspan" :rowspan="row.crewRowspan" class="schedule-merge-cell">{{ row.driver_name || '未安排' }}</td>
            <td v-if="row.crewRowspan" :rowspan="row.crewRowspan" class="schedule-merge-cell">{{ row.assistant_names || '—' }}</td>
            <td>
              <div class="schedule-project">{{ row.project_name || row.task_type || '-' }}</div>
              <div class="schedule-sub">{{ formatTime(row) }} · {{ row.status }}</div>
            </td>
            <td class="plant-detail-cell">
              <div v-for="(line, index) in row.plantLines" :key="`${row.id || row.task_no}-${index}`">{{ line }}</div>
            </td>
          </tr>
        </tbody>
      </table>
    </article>

    <el-dialog v-model="dialogVisible" :title="`${editingId ? '编辑' : '新增'}日程安排`" width="900px" top="5vh" destroy-on-close>
      <el-form label-position="top">
        <section class="form-section">
          <div class="form-grid three">
            <el-form-item label="安排单号" required><el-input v-model="form.task_no" /></el-form-item>
            <el-form-item label="安排日期" required><el-date-picker v-model="form.schedule_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
            <el-form-item label="任务类型">
              <el-select v-model="form.task_type" style="width:100%">
                <el-option label="配送" value="配送" />
                <el-option label="撤花" value="撤花" />
                <el-option label="换花" value="换花" />
                <el-option label="修剪打药" value="修剪打药" />
                <el-option label="其他" value="其他" />
              </el-select>
            </el-form-item>
            <el-form-item label="来源类型">
              <el-select v-model="form.source_type" style="width:100%">
                <el-option label="手工" value="手工" />
                <el-option label="订单" value="订单" />
                <el-option label="出库单" value="出库单" />
                <el-option label="临时安排" value="临时安排" />
              </el-select>
            </el-form-item>
            <el-form-item label="来源单号"><el-input v-model="form.source_no" placeholder="例如：DD-001 / CK-001" /></el-form-item>
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width:100%">
                <el-option label="待发布" value="待发布" />
                <el-option label="已发布" value="已发布" />
            <el-option label="配送中" value="配送中" />
            <el-option label="已送达" value="已送达" />
            <el-option label="已完成" value="已完成" />
                <el-option label="已取消" value="已取消" />
              </el-select>
            </el-form-item>
            <el-form-item label="项目/任务名称" required><el-input v-model="form.project_name" /></el-form-item>
            <el-form-item label="地址"><el-input v-model="form.address" /></el-form-item>
            <div class="dispatch-assignment-row">
              <el-form-item label="车辆">
                <el-select v-model="form.vehicle_id" filterable clearable style="width:100%">
                  <el-option v-for="vehicle in vehicles" :key="vehicle.id" :label="`${vehicle.plate_no} ${vehicle.vehicle_type || ''}`" :value="vehicle.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="司机" required>
                <el-select v-model="form.driver_id" filterable clearable style="width:100%">
                  <el-option v-for="employee in employees" :key="employee.id" :label="`${employee.name} ${employee.position || employee.role || ''}`" :value="employee.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="跟车人员">
                <el-select v-model="form.assistant_ids" multiple filterable clearable style="width:100%">
                  <el-option v-for="employee in employees" :key="employee.id" :label="`${employee.name} ${employee.position || employee.role || ''}`" :value="employee.id" />
                </el-select>
              </el-form-item>
            </div>
            <el-form-item label="计划时间">
              <div class="inline-time-range">
                <el-time-picker v-model="form.planned_start" value-format="HH:mm" format="HH:mm" placeholder="开始" />
                <span>至</span>
                <el-time-picker v-model="form.planned_end" value-format="HH:mm" format="HH:mm" placeholder="结束" />
              </div>
            </el-form-item>
            <el-form-item label="植物/任务清单" required class="wide">
              <el-input v-model="form.item_summary" type="textarea" :rows="4" placeholder="例如：金融中心 A栋8楼 总经理办公室，幸福树 × 1盆；绿萝 × 10盆" />
            </el-form-item>
            <el-form-item label="备注" class="wide"><el-input v-model="form.notes" type="textarea" :rows="3" /></el-form-item>
          </div>
        </section>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="success" :loading="saving" @click="saveTask">保存安排</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.schedule-sheet-panel {
  padding: 18px 22px 26px;
}

.schedule-filter-bar {
  display: grid;
  grid-template-columns: auto minmax(140px, 1fr) auto minmax(150px, 1fr) auto minmax(130px, 1fr) auto minmax(260px, 1.6fr) auto auto;
  align-items: center;
  gap: 10px 12px;
  padding: 12px 14px;
  border: 1px solid #dfe7ef;
  background: #fff;
}

.schedule-filter-bar label {
  color: #26364a;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
}

.schedule-filter-bar :deep(.el-input),
.schedule-filter-bar :deep(.el-select),
.schedule-filter-bar :deep(.el-date-editor) {
  width: 100%;
}

.schedule-sheet-title {
  margin-top: 10px;
  height: 34px;
  line-height: 34px;
  text-align: center;
  color: #21415d;
  font-weight: 700;
  background: #cfe8ff;
  border: 1px solid #c8dff3;
}

.schedule-sheet-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  background: #fff;
  color: #243448;
  font-size: 14px;
}

.schedule-sheet-table th {
  height: 38px;
  background: #cfe8ff;
  border: 1px solid #dce4ec;
  color: #22384f;
  font-weight: 700;
}

.schedule-sheet-table td {
  min-height: 54px;
  padding: 12px 14px;
  text-align: center;
  vertical-align: middle;
  border: 1px solid #e1e5ea;
  line-height: 1.7;
}

.schedule-sheet-table th:nth-child(1) { width: 10%; }
.schedule-sheet-table th:nth-child(2) { width: 10%; }
.schedule-sheet-table th:nth-child(3) { width: 20%; }
.schedule-sheet-table th:nth-child(4) { width: 20%; }
.schedule-sheet-table th:nth-child(5) { width: 20%; }
.schedule-sheet-table th:nth-child(6) { width: 20%; }

.schedule-date-cell {
  color: #1f344b;
  font-weight: 600;
}

.schedule-merge-cell {
  color: #1f344b;
  font-weight: 600;
  text-align: center;
  vertical-align: middle !important;
}

.schedule-project {
  font-weight: 600;
}

.schedule-sub {
  margin-top: 4px;
  color: #7b8a9a;
  font-size: 12px;
}

.plant-detail-cell {
  padding: 0 !important;
}

.plant-detail-cell div {
  padding: 7px 12px;
  border-bottom: 1px solid #e8edf2;
}

.plant-detail-cell div:last-child {
  border-bottom: 0;
}

.empty-cell {
  height: 120px;
  color: #93a0ad;
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

@media (max-width: 1300px) {
  .schedule-filter-bar {
    grid-template-columns: auto minmax(160px, 1fr) auto minmax(160px, 1fr) auto minmax(160px, 1fr);
  }

  .schedule-filter-bar label:nth-of-type(4) {
    grid-column: 1;
  }

  .schedule-filter-bar .el-button {
    min-width: 88px;
  }
}
</style>
