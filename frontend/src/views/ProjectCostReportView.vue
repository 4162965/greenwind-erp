<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowDown, Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const today = new Date()
const year = today.getFullYear()
const loading = ref(false)
const projects = ref<Row[]>([])
const rows = ref<Row[]>([])
const details = ref<Row[]>([])
const expenses = ref<Row[]>([])
const summary = ref<Row>({})
const note = ref('')
const expenseVisible = ref(false)
const savingExpense = ref(false)
const editingExpenseId = ref<number | null>(null)
const filters = ref({
  project_id: null as number | null,
  start_date: `${year}-01-01`,
  end_date: `${year}-12-31`,
})
const expenseForm = ref<Row>({})
const expenseTypes = ['涓村伐璐圭敤', '宸ュ叿鑰楁潗', '鑽搧鑲ユ枡', '蹇€掔墿娴?, '鍋滆溅杩囪矾', '鍏朵粬璐圭敤']

const profitableCount = computed(() => rows.value.filter((row) => Number(row.profit || 0) >= 0).length)

function formatNumber(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') return '0'
  const number = Number(value)
  if (Number.isNaN(number)) return '0'
  return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
}

function formatMoney(value: number | string | null | undefined) {
  return `楼${formatNumber(value)}`
}

function profitType(value: number | string | null | undefined) {
  return Number(value || 0) >= 0 ? 'success' : 'danger'
}

async function loadProjects() {
  projects.value = (await api.get('/projects')).data.items
}

async function loadReport() {
  loading.value = true
  try {
    const response = await api.get('/reports/project-costs', { params: filters.value })
    rows.value = response.data.items
    details.value = response.data.details
    summary.value = response.data.summary || {}
    note.value = response.data.note || ''
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '椤圭洰鎴愭湰鎶ヨ〃鍔犺浇澶辫触')
  } finally {
    loading.value = false
  }
}

async function loadExpenses() {
  try {
    expenses.value = (await api.get('/reports/project-expenses', { params: filters.value })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '椤圭洰璐圭敤鍔犺浇澶辫触')
  }
}

function resetFilters() {
  filters.value = { project_id: null, start_date: `${year}-01-01`, end_date: `${year}-12-31` }
  loadAll()
}

function emptyExpense() {
  return {
    project_id: filters.value.project_id,
    expense_date: new Date().toISOString().slice(0, 10),
    expense_type: '涓村伐璐圭敤',
    amount: null,
    handler: '',
    source_no: '',
    description: '',
    status: '宸茬‘璁?,
  }
}

function openCreateExpense() {
  editingExpenseId.value = null
  expenseForm.value = emptyExpense()
  expenseVisible.value = true
}

function openEditExpense(row: Row) {
  editingExpenseId.value = row.id
  expenseForm.value = { ...row }
  expenseVisible.value = true
}

async function saveExpense() {
  if (!expenseForm.value.project_id) {
    ElMessage.warning('璇烽€夋嫨椤圭洰')
    return
  }
  if (Number(expenseForm.value.amount || 0) <= 0) {
    ElMessage.warning('璇峰～鍐欏ぇ浜?0 鐨勮垂鐢ㄩ噾棰?)
    return
  }
  savingExpense.value = true
  try {
    if (editingExpenseId.value) await api.put(`/reports/project-expenses/${editingExpenseId.value}`, expenseForm.value)
    else await api.post('/reports/project-expenses', expenseForm.value)
    ElMessage.success(`椤圭洰璐圭敤宸?{editingExpenseId.value ? '淇敼' : '鐧昏'}`)
    expenseVisible.value = false
    await loadAll()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '椤圭洰璐圭敤淇濆瓨澶辫触')
  } finally {
    savingExpense.value = false
  }
}

async function deleteExpense(row: Row) {
  await ElMessageBox.confirm(`纭鍒犻櫎杩欐潯鈥?{row.expense_type}鈥濊垂鐢ㄥ悧锛焋, '鍒犻櫎椤圭洰璐圭敤', { type: 'warning' })
  try {
    await api.delete(`/reports/project-expenses/${row.id}`)
    ElMessage.success('椤圭洰璐圭敤宸插垹闄?)
    await loadAll()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '椤圭洰璐圭敤鍒犻櫎澶辫触')
  }
}

async function loadAll() {
  await Promise.all([loadReport(), loadExpenses()])
}

loadProjects()
loadAll()
</script>

<template>
  <div class="page cost-report-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">PROJECT COST</p>
        <h1>椤圭洰鎴愭湰涓績</h1>
        <p>鎸夐」鐩眹鎬诲悎鍚屾姌绠楁敹鍏ャ€侀噰璐垚鏈€佸簱瀛橀鐢ㄣ€佸吇鎶ゅ伐璧勫拰鐗╂祦璐圭敤锛屽厛鐪嬮」鐩槸鍚﹁禋閽便€?/p>
      </div>
    </div>

    <div class="inventory-summary cost-summary">
      <div><span>鍚堝悓鎶樼畻鏀跺叆</span><strong>{{ formatMoney(summary.customer_income) }}</strong></div>
      <div><span>鎬绘垚鏈?/span><strong>{{ formatMoney(summary.total_cost) }}</strong></div>
      <div><span>鍒╂鼎</span><strong :class="{ danger: Number(summary.profit || 0) < 0 }">{{ formatMoney(summary.profit) }}</strong></div>
      <div><span>鍒╂鼎鐜?/span><strong>{{ formatNumber(summary.profit_rate) }}%</strong></div>
      <div><span>宸叉敹娆?/span><strong>{{ formatMoney(summary.receipt_amount) }}</strong></div>
    </div>
    <div class="inventory-summary finance-summary">
      <div><span>宸插紑绁?/span><strong>{{ formatMoney(summary.invoice_amount) }}</strong></div>
      <div><span>鏈敹娆?/span><strong :class="{ danger: Number(summary.unreceived_amount || 0) > 0 }">{{ formatMoney(summary.unreceived_amount) }}</strong></div>
      <div><span>鐩堝埄椤圭洰</span><strong>{{ profitableCount }} / {{ rows.length }}</strong></div>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar cost-toolbar">
        <el-select v-model="filters.project_id" filterable clearable placeholder="鍏ㄩ儴椤圭洰" @change="loadAll">
          <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
        </el-select>
        <el-date-picker v-model="filters.start_date" value-format="YYYY-MM-DD" placeholder="寮€濮嬫棩鏈? @change="loadAll" />
        <el-date-picker v-model="filters.end_date" value-format="YYYY-MM-DD" placeholder="缁撴潫鏃ユ湡" @change="loadAll" />
        <el-button type="success" plain :icon="Search" @click="loadAll">鏌ヨ</el-button>
        <el-button :icon="Refresh" @click="resetFilters">浠婂勾</el-button>
        <el-button type="success" :icon="Plus" @click="openCreateExpense">鐧昏璐圭敤</el-button>
        <span class="report-note">{{ note }}</span>
      </div>

      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="project_name" label="椤圭洰" min-width="180" fixed />
        <el-table-column label="鍚堝悓鏀跺叆" width="120"><template #default="scope">{{ formatMoney(scope.row.customer_income) }}</template></el-table-column>
        <el-table-column label="閲囪喘鎴愭湰" width="120"><template #default="scope">{{ formatMoney(scope.row.purchase_cost) }}</template></el-table-column>
        <el-table-column label="搴撳瓨棰嗙敤" width="120"><template #default="scope">{{ formatMoney(scope.row.stock_out_cost) }}</template></el-table-column>
        <el-table-column label="鍏绘姢宸ヨ祫" width="120"><template #default="scope">{{ formatMoney(scope.row.salary_cost) }}</template></el-table-column>
        <el-table-column label="鍏朵粬璐圭敤" width="120"><template #default="scope">{{ formatMoney(scope.row.other_cost) }}</template></el-table-column>
        <el-table-column label="鐗╂祦璐圭敤" width="120"><template #default="scope">{{ formatMoney(scope.row.logistics_cost) }}</template></el-table-column>
        <el-table-column label="鎬绘垚鏈? width="120"><template #default="scope">{{ formatMoney(scope.row.total_cost) }}</template></el-table-column>
        <el-table-column label="鍒╂鼎" width="120">
          <template #default="scope"><el-tag :type="profitType(scope.row.profit)">{{ formatMoney(scope.row.profit) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="鍒╂鼎鐜? width="100"><template #default="scope">{{ formatNumber(scope.row.profit_rate) }}%</template></el-table-column>
        <el-table-column label="宸插紑绁? width="120"><template #default="scope">{{ formatMoney(scope.row.invoice_amount) }}</template></el-table-column>
        <el-table-column label="宸叉敹娆? width="120"><template #default="scope">{{ formatMoney(scope.row.receipt_amount) }}</template></el-table-column>
        <el-table-column label="鏈敹娆? width="120"><template #default="scope">{{ formatMoney(scope.row.unreceived_amount) }}</template></el-table-column>
      </el-table>
    </article>

    <article class="panel table-panel">
      <div class="panel-head movement-head">
        <div>
          <h3>椤圭洰璐圭敤鐧昏</h3>
          <p>鐢ㄤ簬鐧昏涓村伐銆佸伐鍏疯€楁潗銆佽嵂鍝佽偉鏂欍€佸揩閫掋€佸仠杞﹁繃璺瓑娌℃湁璧伴噰璐崟鐨勯」鐩垂鐢ㄣ€?/p>
        </div>
        <el-button type="success" :icon="Plus" @click="openCreateExpense">鐧昏璐圭敤</el-button>
      </div>
      <el-table :data="expenses" stripe>
        <el-table-column prop="expense_date" label="鏃ユ湡" width="105" />
        <el-table-column prop="project_name" label="椤圭洰" min-width="160" />
        <el-table-column prop="expense_type" label="璐圭敤绫诲瀷" width="105" />
        <el-table-column label="閲戦" width="110"><template #default="scope">{{ formatMoney(scope.row.amount) }}</template></el-table-column>
        <el-table-column prop="handler" label="缁忔墜浜? width="95" />
        <el-table-column prop="source_no" label="鏉ユ簮/绁ㄦ嵁鍙? min-width="130" />
        <el-table-column prop="description" label="璇存槑" min-width="220" show-overflow-tooltip />
        <el-table-column label="鐘舵€? width="90"><template #default="scope"><el-tag :type="scope.row.status === '宸茬‘璁? ? 'success' : 'info'" size="small">{{ scope.row.status }}</el-tag></template></el-table-column>
        <el-table-column label="鎿嶄綔" width="95">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="openEditExpense(scope.row)">缂栬緫</el-dropdown-item>
                  <el-dropdown-item divided @click="deleteExpense(scope.row)">鍒犻櫎</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <article class="panel table-panel">
      <div class="panel-head movement-head">
        <div>
          <h3>璐圭敤鏄庣粏</h3>
          <p>鏈€澶氭樉绀烘渶杩?300 鏉★紝鐢ㄦ潵鏍稿姣忎釜鏀跺叆鎴栨垚鏈潵鑷摢寮犲崟銆?/p>
        </div>
      </div>
      <el-table :data="details" stripe>
        <el-table-column prop="date" label="鏃ユ湡" width="105" />
        <el-table-column prop="project_name" label="椤圭洰" min-width="160" />
        <el-table-column prop="category" label="绫诲埆" width="105" />
        <el-table-column prop="source_no" label="鏉ユ簮鍗曞彿" min-width="135" />
        <el-table-column prop="description" label="璇存槑" min-width="230" show-overflow-tooltip />
        <el-table-column label="鏀跺叆" width="110"><template #default="scope">{{ scope.row.income ? formatMoney(scope.row.income) : '鈥? }}</template></el-table-column>
        <el-table-column label="鎴愭湰" width="110"><template #default="scope">{{ scope.row.cost ? formatMoney(scope.row.cost) : '鈥? }}</template></el-table-column>
      </el-table>
    </article>

    <el-dialog v-model="expenseVisible" :title="`${editingExpenseId ? '缂栬緫' : '鐧昏'}椤圭洰璐圭敤`" width="720px" destroy-on-close>
      <el-form label-position="top">
        <div class="form-grid two">
          <el-form-item label="椤圭洰" required>
            <el-select v-model="expenseForm.project_id" filterable style="width:100%">
              <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="璐圭敤鏃ユ湡" required>
            <el-date-picker v-model="expenseForm.expense_date" value-format="YYYY-MM-DD" style="width:100%" />
          </el-form-item>
          <el-form-item label="璐圭敤绫诲瀷">
            <el-select v-model="expenseForm.expense_type" filterable allow-create style="width:100%">
              <el-option v-for="type in expenseTypes" :key="type" :label="type" :value="type" />
            </el-select>
          </el-form-item>
          <el-form-item label="閲戦" required>
            <el-input-number v-model="expenseForm.amount" :min="0" :controls="false" style="width:100%" />
          </el-form-item>
          <el-form-item label="缁忔墜浜?><el-input v-model="expenseForm.handler" placeholder="璋佸彂鐢?鐧昏鐨勮垂鐢? /></el-form-item>
          <el-form-item label="鏉ユ簮/绁ㄦ嵁鍙?><el-input v-model="expenseForm.source_no" placeholder="鍙～鍙戠エ鍙枫€佹敹鎹彿銆佽揣鎷夋媺鍗曞彿绛? /></el-form-item>
          <el-form-item label="鐘舵€?>
            <el-select v-model="expenseForm.status" style="width:100%">
              <el-option label="宸茬‘璁? value="宸茬‘璁? />
              <el-option label="寰呯‘璁? value="寰呯‘璁? />
              <el-option label="浣滃簾" value="浣滃簾" />
            </el-select>
          </el-form-item>
          <el-form-item label="璇存槑" class="wide">
            <el-input v-model="expenseForm.description" type="textarea" :rows="3" placeholder="渚嬪锛氫复宸?浜轰慨鍓崐澶┿€侀」鐩喘涔版墦鑽伐鍏枫€佽揣鎷夋媺琛ュ樊浠风瓑" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="expenseVisible=false">鍙栨秷</el-button>
        <el-button type="success" :loading="savingExpense" @click="saveExpense">淇濆瓨璐圭敤</el-button>
      </template>
    </el-dialog>
  </div>
</template>

