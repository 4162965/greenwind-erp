<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ArrowDown, Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const statusFilter = ref('')
const rows = ref<Row[]>([])
const projects = ref<Row[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<Row>({})
const businessOptions = ['绉熸憜', '瀹ゅ鍏绘姢', '閿€鍞?, '鎹㈣姳', '宸ョ▼鍏绘姢', '鍏朵粬']

const activeContracts = computed(() => rows.value.filter((row) => row.status === '鐢熸晥').length)
const expiringContracts = computed(() => rows.value.filter((row) => isExpiring(row)).length)
const totalAmount = computed(() => rows.value.reduce((sum, row) => sum + Number(row.amount || 0), 0))

function formatNumber(value: number | string | null | undefined) {
  const number = Number(value || 0)
  if (!number) return '0'
  return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
}

function money(value: number | string | null | undefined) {
  return `楼${formatNumber(value)}`
}

function daysLeft(row: Row) {
  if (!row.end_date) return null
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const end = new Date(row.end_date)
  end.setHours(0, 0, 0, 0)
  return Math.ceil((end.getTime() - today.getTime()) / 86400000)
}

function isExpiring(row: Row) {
  const left = daysLeft(row)
  return row.status === '鐢熸晥' && left !== null && left >= 0 && left <= Number(row.reminder_days || 0)
}

function contractTag(row: Row) {
  const left = daysLeft(row)
  if (row.status !== '鐢熸晥') return 'info'
  if (left !== null && left < 0) return 'danger'
  if (isExpiring(row)) return 'warning'
  return 'success'
}

function contractStatusText(row: Row) {
  const left = daysLeft(row)
  if (row.status !== '鐢熸晥') return row.status
  if (left !== null && left < 0) return '宸插埌鏈?
  if (isExpiring(row)) return `鍗冲皢鍒版湡锝滃墿${left}澶ー
  return '鐢熸晥'
}

function resetForm(values: Row) {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, values)
}

function emptyContract() {
  return {
    project_id: null,
    contract_no: `HT-${Date.now().toString().slice(-8)}`,
    name: '',
    contract_type: '鏁翠綋鍚堝悓',
    business_types: ['绉熸憜'],
    effective_date: '',
    end_date: '',
    billing_start_date: '',
    billing_cycle: '鏈堜粯',
    amount: 0,
    reminder_days: 30,
    status: '鐢熸晥',
    notes: '',
  }
}

function normalizePayload() {
  return {
    ...form,
    business_types: Array.isArray(form.business_types) ? form.business_types.join(',') : form.business_types || '',
    billing_start_date: form.billing_start_date || null,
  }
}

async function loadProjects() {
  projects.value = (await api.get('/projects')).data.items
}

async function loadRows() {
  loading.value = true
  try {
    const response = await api.get('/contracts', { params: { keyword: keyword.value.trim() } })
    rows.value = response.data.items.filter((row: Row) => !statusFilter.value || row.status === statusFilter.value || (statusFilter.value === '鍗冲皢鍒版湡' && isExpiring(row)))
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鍚堝悓鍔犺浇澶辫触')
  } finally {
    loading.value = false
  }
}

async function openCreate() {
  await loadProjects()
  editingId.value = null
  resetForm(emptyContract())
  dialogVisible.value = true
}

async function openEdit(row: Row) {
  await loadProjects()
  editingId.value = row.id
  resetForm({ ...row, business_types: String(row.business_types || '').split(',').filter(Boolean) })
  dialogVisible.value = true
}

async function saveContract() {
  if (!form.project_id) {
    ElMessage.warning('璇烽€夋嫨椤圭洰')
    return
  }
  if (!form.contract_no || !form.name) {
    ElMessage.warning('璇峰～鍐欏悎鍚岀紪鍙峰拰鍚堝悓鍚嶇О')
    return
  }
  if (!form.effective_date || !form.end_date) {
    ElMessage.warning('璇峰～鍐欏悎鍚岀敓鏁堟棩鏈熷拰缁撴潫鏃ユ湡')
    return
  }
  saving.value = true
  try {
    const payload = normalizePayload()
    if (editingId.value) await api.put(`/contracts/${editingId.value}`, payload)
    else await api.post('/contracts', payload)
    ElMessage.success(`鍚堝悓宸?{editingId.value ? '淇敼' : '鏂板'}`)
    dialogVisible.value = false
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鍚堝悓淇濆瓨澶辫触')
  } finally {
    saving.value = false
  }
}

async function deleteContract(row: Row) {
  await ElMessageBox.confirm(`纭鍒犻櫎鍚堝悓鈥?{row.contract_no}鈥濆悧锛焋, '鍒犻櫎鍚堝悓', { type: 'warning' })
  try {
    await api.delete(`/contracts/${row.id}`)
    ElMessage.success('鍚堝悓宸插垹闄?)
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鍚堝悓鍒犻櫎澶辫触')
  }
}

loadProjects()
loadRows()
</script>

<template>
  <div class="page contract-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">CONTRACT</p>
        <h1>鍚堝悓绠＄悊</h1>
        <p>缁熶竴鏌ョ湅鏁翠綋鍚堝悓銆佸垎浣撳悎鍚屻€佽璐瑰紑濮嬫棩銆佷粯娆惧懆鏈熴€佸埌鏈熸彁閱掑拰鍚堝悓閲戦銆?/p>
      </div>
      <el-button type="success" :icon="Plus" @click="openCreate">鏂板鍚堝悓</el-button>
    </div>

    <div class="inventory-summary contract-summary">
      <div><span>鍚堝悓鏁伴噺</span><strong>{{ rows.length }}</strong></div>
      <div><span>鐢熸晥鍚堝悓</span><strong>{{ activeContracts }}</strong></div>
      <div><span>鍗冲皢鍒版湡</span><strong :class="{ danger: expiringContracts > 0 }">{{ expiringContracts }}</strong></div>
      <div><span>鍚堝悓閲戦鍚堣</span><strong>{{ money(totalAmount) }}</strong></div>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="鎼滅储鍚堝悓缂栧彿銆佸悎鍚屽悕绉? @keyup.enter="loadRows" @clear="loadRows" />
        <el-select v-model="statusFilter" clearable placeholder="鍚堝悓鐘舵€? @change="loadRows">
          <el-option label="鐢熸晥" value="鐢熸晥" />
          <el-option label="鍗冲皢鍒版湡" value="鍗冲皢鍒版湡" />
          <el-option label="鑽夌" value="鑽夌" />
          <el-option label="鏆傚仠" value="鏆傚仠" />
          <el-option label="鍒版湡" value="鍒版湡" />
          <el-option label="缁堟" value="缁堟" />
        </el-select>
        <el-button type="success" plain :icon="Search" @click="loadRows">鏌ヨ</el-button>
        <el-button :icon="Refresh" @click="keyword=''; statusFilter=''; loadRows()">閲嶇疆</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="contract_no" label="鍚堝悓缂栧彿" min-width="135" fixed />
        <el-table-column prop="name" label="鍚堝悓鍚嶇О" min-width="180" show-overflow-tooltip />
        <el-table-column prop="project_name" label="椤圭洰" min-width="160" />
        <el-table-column prop="contract_type" label="绫诲瀷" width="95" />
        <el-table-column prop="business_types" label="涓氬姟" min-width="120" show-overflow-tooltip />
        <el-table-column prop="effective_date" label="鐢熸晥鏃? width="105" />
        <el-table-column prop="end_date" label="缁撴潫鏃? width="105" />
        <el-table-column prop="billing_start_date" label="璁¤垂寮€濮? width="105" />
        <el-table-column prop="billing_cycle" label="浠樻鍛ㄦ湡" width="95" />
        <el-table-column label="閲戦" width="115"><template #default="scope">{{ money(scope.row.amount) }}</template></el-table-column>
        <el-table-column label="鎻愰啋" width="135">
          <template #default="scope"><el-tag :type="contractTag(scope.row)" size="small">{{ contractStatusText(scope.row) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="notes" label="澶囨敞" min-width="160" show-overflow-tooltip />
        <el-table-column label="鎿嶄綔" width="95">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="openEdit(scope.row)">缂栬緫</el-dropdown-item>
                  <el-dropdown-item divided @click="deleteContract(scope.row)">鍒犻櫎</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <el-dialog v-model="dialogVisible" :title="`${editingId ? '缂栬緫' : '鏂板'}鍚堝悓`" width="820px" destroy-on-close>
      <el-form label-position="top">
        <div class="form-grid two">
          <el-form-item label="椤圭洰" required>
            <el-select v-model="form.project_id" filterable style="width:100%">
              <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="鍚堝悓缂栧彿" required><el-input v-model="form.contract_no" /></el-form-item>
          <el-form-item label="鍚堝悓鍚嶇О" required><el-input v-model="form.name" /></el-form-item>
          <el-form-item label="鍚堝悓绫诲瀷">
            <el-select v-model="form.contract_type" style="width:100%">
              <el-option label="鏁翠綋鍚堝悓" value="鏁翠綋鍚堝悓" />
              <el-option label="鍒嗕綋鍚堝悓" value="鍒嗕綋鍚堝悓" />
            </el-select>
          </el-form-item>
          <el-form-item label="瑕嗙洊涓氬姟">
            <el-select v-model="form.business_types" multiple style="width:100%">
              <el-option v-for="item in businessOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="浠樻鍛ㄦ湡">
            <el-select v-model="form.billing_cycle" allow-create filterable style="width:100%">
              <el-option v-for="item in ['鏈堜粯','瀛ｄ粯','鍗婂勾浠?,'骞翠粯','涓€娆℃€?,'鑷畾涔?]" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="鐢熸晥鏃ユ湡" required><el-date-picker v-model="form.effective_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
          <el-form-item label="缁撴潫鏃ユ湡" required><el-date-picker v-model="form.end_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
          <el-form-item label="璁¤垂寮€濮嬫棩鏈?><el-date-picker v-model="form.billing_start_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
          <el-form-item label="鍚堝悓閲戦"><el-input-number v-model="form.amount" :min="0" :controls="false" style="width:100%" /></el-form-item>
          <el-form-item label="鎻愬墠鎻愰啋澶╂暟"><el-input-number v-model="form.reminder_days" :min="0" :controls="false" style="width:100%" /></el-form-item>
          <el-form-item label="鐘舵€?>
            <el-select v-model="form.status" style="width:100%">
              <el-option v-for="item in ['鑽夌','鐢熸晥','鏆傚仠','鍒版湡','缁堟']" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="澶囨敞" class="wide"><el-input v-model="form.notes" type="textarea" :rows="3" /></el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">鍙栨秷</el-button>
        <el-button type="success" :loading="saving" @click="saveContract">淇濆瓨鍚堝悓</el-button>
      </template>
    </el-dialog>
  </div>
</template>

