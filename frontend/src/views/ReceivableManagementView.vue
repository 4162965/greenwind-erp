<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ArrowDown, Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const loading = ref(false)
const saving = ref(false)
const generating = ref(false)
const keyword = ref('')
const statusFilter = ref('')
const rows = ref<Row[]>([])
const projects = ref<Row[]>([])
const contracts = ref<Row[]>([])
const dialogVisible = ref(false)
const generateVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<Row>({})
const generateForm = reactive({ contract_id: null as number | null })

const summary = computed(() => {
  const amount = rows.value.reduce((sum, row) => sum + Number(row.amount || 0), 0)
  const received = rows.value.reduce((sum, row) => sum + Number(row.received_amount || 0), 0)
  const invoiced = rows.value.reduce((sum, row) => sum + Number(row.invoice_amount || 0), 0)
  return { amount, received, invoiced, unreceived: amount - received }
})

function formatNumber(value: number | string | null | undefined) {
  const number = Number(value || 0)
  if (!number) return '0'
  return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
}

function money(value: number | string | null | undefined) {
  return `楼${formatNumber(value)}`
}

function statusType(status: string) {
  if (status === '宸叉敹娆?) return 'success'
  if (status === '閮ㄥ垎鏀舵') return 'warning'
  if (status === '閫炬湡') return 'danger'
  return 'info'
}

function resetForm(values: Row) {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, values)
}

function emptyReceivable() {
  return {
    receivable_no: `YS-${Date.now().toString().slice(-8)}`,
    project_id: null,
    contract_id: null,
    billing_period: new Date().toISOString().slice(0, 7),
    due_date: new Date().toISOString().slice(0, 10),
    amount: null,
    receivable_type: '鍚堝悓搴旀敹',
    status: '寰呮敹娆?,
    notes: '',
  }
}

async function loadProjects() {
  projects.value = (await api.get('/projects')).data.items
}

async function loadContracts() {
  contracts.value = (await api.get('/contracts')).data.items
}

async function loadRows() {
  loading.value = true
  try {
    rows.value = (await api.get('/finance/receivables', { params: { keyword: keyword.value.trim(), status: statusFilter.value } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '搴旀敹璐︽湡鍔犺浇澶辫触')
  } finally {
    loading.value = false
  }
}

async function openCreate() {
  await Promise.all([loadProjects(), loadContracts()])
  editingId.value = null
  resetForm(emptyReceivable())
  dialogVisible.value = true
}

async function openEdit(row: Row) {
  await Promise.all([loadProjects(), loadContracts()])
  editingId.value = row.id
  resetForm({ ...row })
  dialogVisible.value = true
}

async function saveReceivable() {
  if (!form.project_id) {
    ElMessage.warning('璇烽€夋嫨椤圭洰')
    return
  }
  if (!form.receivable_no) {
    ElMessage.warning('璇峰～鍐欏簲鏀剁紪鍙?)
    return
  }
  if (Number(form.amount || 0) <= 0) {
    ElMessage.warning('搴旀敹閲戦蹇呴』澶т簬0')
    return
  }
  saving.value = true
  try {
    if (editingId.value) await api.put(`/finance/receivables/${editingId.value}`, form)
    else await api.post('/finance/receivables', form)
    ElMessage.success(`搴旀敹璐︽湡宸?{editingId.value ? '淇敼' : '鏂板'}`)
    dialogVisible.value = false
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '搴旀敹璐︽湡淇濆瓨澶辫触')
  } finally {
    saving.value = false
  }
}

async function deleteReceivable(row: Row) {
  await ElMessageBox.confirm(`纭鍒犻櫎搴旀敹鈥?{row.receivable_no}鈥濆悧锛焋, '鍒犻櫎搴旀敹璐︽湡', { type: 'warning' })
  try {
    await api.delete(`/finance/receivables/${row.id}`)
    ElMessage.success('搴旀敹璐︽湡宸插垹闄?)
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '搴旀敹璐︽湡鍒犻櫎澶辫触')
  }
}

async function openGenerate() {
  await loadContracts()
  generateForm.contract_id = null
  generateVisible.value = true
}

async function generateFromContract() {
  if (!generateForm.contract_id) {
    ElMessage.warning('璇烽€夋嫨鍚堝悓')
    return
  }
  generating.value = true
  try {
    const response = await api.post(`/finance/receivables/generate-from-contract/${generateForm.contract_id}`)
    ElMessage.success(`鐢熸垚瀹屾垚锛氭柊澧?${response.data.created} 鏉★紝璺宠繃 ${response.data.skipped} 鏉)
    generateVisible.value = false
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鐢熸垚搴旀敹璐︽湡澶辫触')
  } finally {
    generating.value = false
  }
}

loadProjects()
loadContracts()
loadRows()
</script>

<template>
  <div class="page receivable-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">RECEIVABLE</p>
        <h1>搴旀敹璐︽湡</h1>
        <p>鎸夊悎鍚屼粯娆惧懆鏈熺敓鎴愭瘡鏈熷簲鏀讹紝骞惰嚜鍔ㄦ牳瀵瑰悓椤圭洰銆佸悓鍚堝悓銆佸悓璐︽湡鐨勫紑绁ㄥ拰鏀舵銆?/p>
      </div>
      <div class="page-actions">
        <el-button :icon="Refresh" @click="openGenerate">浠庡悎鍚岀敓鎴?/el-button>
        <el-button type="success" :icon="Plus" @click="openCreate">鏂板搴旀敹</el-button>
      </div>
    </div>

    <div class="inventory-summary receivable-summary">
      <div><span>搴旀敹閲戦</span><strong>{{ money(summary.amount) }}</strong></div>
      <div><span>宸插紑绁?/span><strong>{{ money(summary.invoiced) }}</strong></div>
      <div><span>宸叉敹娆?/span><strong>{{ money(summary.received) }}</strong></div>
      <div><span>鏈敹娆?/span><strong :class="{ danger: summary.unreceived > 0 }">{{ money(summary.unreceived) }}</strong></div>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="鎼滅储搴旀敹缂栧彿銆佽处鏈熴€佸娉? @keyup.enter="loadRows" @clear="loadRows" />
        <el-select v-model="statusFilter" clearable placeholder="搴旀敹鐘舵€? @change="loadRows">
          <el-option label="寰呮敹娆? value="寰呮敹娆? />
          <el-option label="閮ㄥ垎鏀舵" value="閮ㄥ垎鏀舵" />
          <el-option label="宸叉敹娆? value="宸叉敹娆? />
          <el-option label="閫炬湡" value="閫炬湡" />
        </el-select>
        <el-button type="success" plain :icon="Search" @click="loadRows">鏌ヨ</el-button>
        <el-button :icon="Refresh" @click="keyword=''; statusFilter=''; loadRows()">閲嶇疆</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="receivable_no" label="搴旀敹缂栧彿" min-width="145" fixed />
        <el-table-column prop="project_name" label="椤圭洰" min-width="160" />
        <el-table-column prop="contract_no" label="鍚堝悓缂栧彿" min-width="130" />
        <el-table-column prop="contract_name" label="鍚堝悓" min-width="150" show-overflow-tooltip />
        <el-table-column prop="billing_period" label="璐︽湡" width="120" />
        <el-table-column prop="due_date" label="搴旀敹鏃ユ湡" width="105" />
        <el-table-column label="搴旀敹閲戦" width="115"><template #default="scope">{{ money(scope.row.amount) }}</template></el-table-column>
        <el-table-column label="宸插紑绁? width="110"><template #default="scope">{{ money(scope.row.invoice_amount) }}</template></el-table-column>
        <el-table-column label="宸叉敹娆? width="110"><template #default="scope">{{ money(scope.row.received_amount) }}</template></el-table-column>
        <el-table-column label="鏈敹娆? width="110"><template #default="scope">{{ money(scope.row.unreceived_amount) }}</template></el-table-column>
        <el-table-column prop="receivable_type" label="绫诲瀷" width="100" />
        <el-table-column label="鐘舵€? width="95"><template #default="scope"><el-tag :type="statusType(scope.row.status)" size="small">{{ scope.row.status }}</el-tag></template></el-table-column>
        <el-table-column prop="notes" label="澶囨敞" min-width="160" show-overflow-tooltip />
        <el-table-column label="鎿嶄綔" width="95">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="openEdit(scope.row)">缂栬緫</el-dropdown-item>
                  <el-dropdown-item divided @click="deleteReceivable(scope.row)">鍒犻櫎</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <el-dialog v-model="dialogVisible" :title="`${editingId ? '缂栬緫' : '鏂板'}搴旀敹璐︽湡`" width="760px" destroy-on-close>
      <el-form label-position="top">
        <div class="form-grid two">
          <el-form-item label="搴旀敹缂栧彿" required><el-input v-model="form.receivable_no" /></el-form-item>
          <el-form-item label="椤圭洰" required>
            <el-select v-model="form.project_id" filterable style="width:100%">
              <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="鍏宠仈鍚堝悓">
            <el-select v-model="form.contract_id" clearable filterable style="width:100%">
              <el-option v-for="contract in contracts" :key="contract.id" :label="`${contract.contract_no}锝?{contract.name}`" :value="contract.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="璐︽湡"><el-input v-model="form.billing_period" placeholder="渚嬪锛?026-08" /></el-form-item>
          <el-form-item label="搴旀敹鏃ユ湡" required><el-date-picker v-model="form.due_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
          <el-form-item label="搴旀敹閲戦" required><el-input-number v-model="form.amount" :min="0" :controls="false" style="width:100%" /></el-form-item>
          <el-form-item label="绫诲瀷">
            <el-select v-model="form.receivable_type" allow-create filterable style="width:100%">
              <el-option label="鍚堝悓搴旀敹" value="鍚堝悓搴旀敹" />
              <el-option label="涓存椂閿€鍞簲鏀? value="涓存椂閿€鍞簲鏀? />
              <el-option label="鍏朵粬搴旀敹" value="鍏朵粬搴旀敹" />
            </el-select>
          </el-form-item>
          <el-form-item label="鐘舵€?>
            <el-select v-model="form.status" style="width:100%">
              <el-option label="寰呮敹娆? value="寰呮敹娆? />
              <el-option label="閮ㄥ垎鏀舵" value="閮ㄥ垎鏀舵" />
              <el-option label="宸叉敹娆? value="宸叉敹娆? />
              <el-option label="閫炬湡" value="閫炬湡" />
            </el-select>
          </el-form-item>
          <el-form-item label="澶囨敞" class="wide"><el-input v-model="form.notes" type="textarea" :rows="3" /></el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">鍙栨秷</el-button>
        <el-button type="success" :loading="saving" @click="saveReceivable">淇濆瓨</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="generateVisible" title="浠庡悎鍚岀敓鎴愬簲鏀惰处鏈? width="560px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="閫夋嫨鍚堝悓" required>
          <el-select v-model="generateForm.contract_id" filterable style="width:100%">
            <el-option
              v-for="contract in contracts"
              :key="contract.id"
              :label="`${contract.contract_no}锝?{contract.project_name}锝?{contract.billing_cycle}锝?{money(contract.amount)}`"
              :value="contract.id"
            />
          </el-select>
        </el-form-item>
        <p class="form-hint">绯荤粺浼氭牴鎹悎鍚岄噾棰濄€佽璐瑰紑濮嬫棩銆佺粨鏉熸棩鍜屼粯娆惧懆鏈熺敓鎴愯处鏈燂紱宸茬敓鎴愯繃鐨勭紪鍙蜂細鑷姩璺宠繃銆?/p>
      </el-form>
      <template #footer>
        <el-button @click="generateVisible=false">鍙栨秷</el-button>
        <el-button type="success" :loading="generating" @click="generateFromContract">鐢熸垚璐︽湡</el-button>
      </template>
    </el-dialog>
  </div>
</template>

