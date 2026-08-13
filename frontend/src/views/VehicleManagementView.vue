<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ArrowDown, Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const rows = ref<Row[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<Row>({})

const reminderSummary = computed(() => ({
  total: rows.value.length,
  expired: rows.value.filter((row) => row.reminder_status === '宸茶繃鏈?).length,
  upcoming: rows.value.filter((row) => row.reminder_status === '鍗冲皢鍒版湡').length,
  available: rows.value.filter((row) => row.status === '鍙敤').length,
}))

function resetForm(values: Row) {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, values)
}

function emptyVehicle() {
  return {
    plate_no: '',
    vehicle_type: '闈㈠寘杞?,
    driver_name: '',
    status: '鍙敤',
    insurance_expiry: '',
    inspection_expiry: '',
    maintenance_due_date: '',
    reminder_days: 30,
    reminder_to: '',
    notes: '',
  }
}

async function loadRows() {
  loading.value = true
  try {
    rows.value = (await api.get('/vehicles', { params: { keyword: keyword.value.trim() } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '杞﹁締鍒楄〃鍔犺浇澶辫触')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  resetForm(emptyVehicle())
  dialogVisible.value = true
}

function openEdit(row: Row) {
  editingId.value = row.id
  resetForm({
    ...row,
    insurance_expiry: row.insurance_expiry || '',
    inspection_expiry: row.inspection_expiry || '',
    maintenance_due_date: row.maintenance_due_date || '',
    reminder_days: row.reminder_days ?? 30,
    reminder_to: row.reminder_to || '',
  })
  dialogVisible.value = true
}

async function saveVehicle() {
  if (!form.plate_no?.trim()) {
    ElMessage.warning('璇峰～鍐欒溅鐗屽彿')
    return
  }
  saving.value = true
  try {
    const payload = {
      ...form,
      plate_no: form.plate_no.trim(),
      insurance_expiry: form.insurance_expiry || null,
      inspection_expiry: form.inspection_expiry || null,
      maintenance_due_date: form.maintenance_due_date || null,
      reminder_days: Number(form.reminder_days || 0),
      reminder_to: form.reminder_to || '',
    }
    if (editingId.value) await api.put(`/vehicles/${editingId.value}`, payload)
    else await api.post('/vehicles', payload)
    ElMessage.success(`杞﹁締宸?{editingId.value ? '淇敼' : '鏂板'}`)
    dialogVisible.value = false
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '杞﹁締淇濆瓨澶辫触')
  } finally {
    saving.value = false
  }
}

async function deleteVehicle(row: Row) {
  await ElMessageBox.confirm(`纭鍒犻櫎杞﹁締鈥?{row.plate_no}鈥濆悧锛焋, '鍒犻櫎杞﹁締', { type: 'warning' })
  try {
    await api.delete(`/vehicles/${row.id}`)
    ElMessage.success('杞﹁締宸插垹闄?)
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '杞﹁締鍒犻櫎澶辫触')
  }
}

function reminderTagType(status: string) {
  if (status === '宸茶繃鏈?) return 'danger'
  if (status === '鍗冲皢鍒版湡') return 'warning'
  return 'success'
}

loadRows()
</script>

<template>
  <div class="page vehicle-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">VEHICLE</p>
        <h1>杞﹁締绠＄悊</h1>
        <p>鍏堝缓绔嬮厤閫佽溅杈嗘。妗堬紝鍚庨潰姣忔棩瀹夋帓琛ㄥ彲浠ョ洿鎺ラ€夋嫨杞﹁締銆佸徃鏈哄拰璺熻溅浜哄憳銆?/p>
      </div>
      <el-button type="success" :icon="Plus" @click="openCreate">鏂板杞﹁締</el-button>
    </div>

    <section class="vehicle-summary">
      <div><span>杞﹁締鎬绘暟</span><strong>{{ reminderSummary.total }}</strong></div>
      <div><span>鍙敤杞﹁締</span><strong>{{ reminderSummary.available }}</strong></div>
      <div><span>鍗冲皢鍒版湡</span><strong>{{ reminderSummary.upcoming }}</strong></div>
      <div><span>宸茶繃鏈?/span><strong>{{ reminderSummary.expired }}</strong></div>
    </section>

    <article class="panel table-panel">
      <div class="table-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="鎼滅储杞︾墝銆佽溅鍨嬨€侀粯璁ゅ徃鏈? @keyup.enter="loadRows" @clear="loadRows" />
        <el-button type="success" plain :icon="Search" @click="loadRows">鏌ヨ</el-button>
        <el-button :icon="Refresh" @click="keyword=''; loadRows()">閲嶇疆</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="plate_no" label="杞︾墝鍙? min-width="130" />
        <el-table-column prop="vehicle_type" label="杞﹀瀷" width="120" />
        <el-table-column prop="driver_name" label="榛樿鍙告満" width="110" />
        <el-table-column label="鐘舵€? width="90">
          <template #default="scope"><el-tag :type="scope.row.status === '鍙敤' ? 'success' : 'info'">{{ scope.row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="insurance_expiry" label="淇濋櫓鍒版湡" width="120" />
        <el-table-column prop="inspection_expiry" label="骞存鍒版湡" width="120" />
        <el-table-column prop="maintenance_due_date" label="淇濆吇鍒版湡" width="120" />
        <el-table-column label="鎻愰啋鐘舵€? min-width="210">
          <template #default="scope">
            <el-tag :type="reminderTagType(scope.row.reminder_status)">{{ scope.row.reminder_status || '姝ｅ父' }}</el-tag>
            <span v-if="scope.row.reminder_items?.length" class="vehicle-reminder-text">{{ scope.row.reminder_items.join('锛?) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="reminder_to" label="鎻愰啋浜? width="130" show-overflow-tooltip />
        <el-table-column prop="notes" label="澶囨敞" min-width="180" show-overflow-tooltip />
        <el-table-column label="鎿嶄綔" width="95">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="openEdit(scope.row)">缂栬緫</el-dropdown-item>
                  <el-dropdown-item divided @click="deleteVehicle(scope.row)">鍒犻櫎</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <el-dialog v-model="dialogVisible" :title="`${editingId ? '缂栬緫' : '鏂板'}杞﹁締`" width="620px" destroy-on-close>
      <el-form label-position="top">
        <div class="form-grid two">
          <el-form-item label="杞︾墝鍙? required><el-input v-model="form.plate_no" placeholder="渚嬪锛氱菠B12345" /></el-form-item>
          <el-form-item label="杞﹀瀷"><el-input v-model="form.vehicle_type" placeholder="渚嬪锛氶潰鍖呰溅銆佸皬璐ц溅" /></el-form-item>
          <el-form-item label="榛樿鍙告満"><el-input v-model="form.driver_name" placeholder="鍙┖锛屾帓鐝椂浠嶅彲鍗曠嫭閫夋嫨" /></el-form-item>
          <el-form-item label="鐘舵€?>
            <el-select v-model="form.status" style="width:100%">
              <el-option label="鍙敤" value="鍙敤" />
              <el-option label="缁翠慨涓? value="缁翠慨涓? />
              <el-option label="鍋滅敤" value="鍋滅敤" />
            </el-select>
          </el-form-item>
          <el-form-item label="淇濋櫓鍒版湡"><el-date-picker v-model="form.insurance_expiry" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
          <el-form-item label="骞存鍒版湡"><el-date-picker v-model="form.inspection_expiry" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
          <el-form-item label="淇濆吇鍒版湡"><el-date-picker v-model="form.maintenance_due_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
          <el-form-item label="鎻愬墠鎻愰啋澶╂暟"><el-input-number v-model="form.reminder_days" :min="0" :max="365" style="width:100%" /></el-form-item>
          <el-form-item label="鎻愰啋浜?><el-input v-model="form.reminder_to" placeholder="渚嬪锛氬鏈嶃€佷富绠°€佸紶涓? /></el-form-item>
          <el-form-item label="澶囨敞" class="wide"><el-input v-model="form.notes" type="textarea" :rows="3" /></el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">鍙栨秷</el-button>
        <el-button type="success" :loading="saving" @click="saveVehicle">淇濆瓨</el-button>
      </template>
    </el-dialog>
  </div>
</template>

