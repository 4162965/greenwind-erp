<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDown, Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const route = useRoute()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const rows = ref<Row[]>([])
const projects = ref<Row[]>([])
const invoices = ref<Row[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<Row>({})

const isReceipt = computed(() => String(route.params.financeType || '').includes('receipt'))
const meta = computed(() => isReceipt.value
  ? { title: '鏀舵绠＄悊', api: '/finance/receipts', noKey: 'receipt_no', dateKey: 'receipt_date', noLabel: '鏀舵鍗曞彿', amountLabel: '鏀舵閲戦' }
  : { title: '寮€绁ㄧ鐞?, api: '/finance/invoices', noKey: 'invoice_no', dateKey: 'invoice_date', noLabel: '鍙戠エ鍙?, amountLabel: '寮€绁ㄩ噾棰? })

function formatNumber(value: number | string | null | undefined) {
  const number = Number(value || 0)
  if (!number) return '0'
  return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
}

function formatMoney(value: number | string | null | undefined) {
  return `楼${formatNumber(value)}`
}

function resetForm(values: Row) {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, values)
}

function emptyRecord() {
  const prefix = isReceipt.value ? 'SK' : 'FP'
  const dateKey = meta.value.dateKey
  return {
    [meta.value.noKey]: `${prefix}-${Date.now().toString().slice(-8)}`,
    project_id: null,
    contract_id: null,
    invoice_id: null,
    [dateKey]: new Date().toISOString().slice(0, 10),
    billing_period: '',
    amount: null,
    tax_amount: 0,
    invoice_type: '鏅€氬彂绁?,
    payment_method: '閾惰杞处',
    payer_name: '',
    handler: '',
    source_no: '',
    status: isReceipt.value ? '宸叉敹娆? : '宸插紑绁?,
    notes: '',
  }
}

async function loadProjects() {
  projects.value = (await api.get('/projects')).data.items
}

async function loadInvoices() {
  if (!isReceipt.value) return
  invoices.value = (await api.get('/finance/invoices')).data.items
}

async function loadRows() {
  loading.value = true
  try {
    rows.value = (await api.get(meta.value.api, { params: { keyword: keyword.value.trim() } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || `${meta.value.title}鍔犺浇澶辫触`)
  } finally {
    loading.value = false
  }
}

async function openCreate() {
  await Promise.all([loadProjects(), loadInvoices()])
  editingId.value = null
  resetForm(emptyRecord())
  dialogVisible.value = true
}

async function openEdit(row: Row) {
  await Promise.all([loadProjects(), loadInvoices()])
  editingId.value = row.id
  resetForm({ ...row })
  dialogVisible.value = true
}

async function saveRecord() {
  if (!form.project_id) {
    ElMessage.warning('璇烽€夋嫨椤圭洰')
    return
  }
  if (!form[meta.value.noKey]) {
    ElMessage.warning(`璇峰～鍐?{meta.value.noLabel}`)
    return
  }
  if (Number(form.amount || 0) <= 0) {
    ElMessage.warning(`${meta.value.amountLabel}蹇呴』澶т簬0`)
    return
  }
  saving.value = true
  try {
    if (editingId.value) await api.put(`${meta.value.api}/${editingId.value}`, form)
    else await api.post(meta.value.api, form)
    ElMessage.success(`${meta.value.title}璁板綍宸?{editingId.value ? '淇敼' : '鏂板'}`)
    dialogVisible.value = false
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '淇濆瓨澶辫触')
  } finally {
    saving.value = false
  }
}

async function deleteRecord(row: Row) {
  const no = row[meta.value.noKey]
  await ElMessageBox.confirm(`纭鍒犻櫎鈥?{no}鈥濆悧锛焋, `鍒犻櫎${meta.value.title}璁板綍`, { type: 'warning' })
  try {
    await api.delete(`${meta.value.api}/${row.id}`)
    ElMessage.success('璁板綍宸插垹闄?)
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鍒犻櫎澶辫触')
  }
}

watch(() => route.fullPath, () => {
  keyword.value = ''
  loadRows()
})

loadProjects()
loadRows()
</script>

<template>
  <div class="page finance-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">FINANCE</p>
        <h1>{{ meta.title }}</h1>
        <p>{{ isReceipt ? '璁板綍椤圭洰瀹為檯鍒拌处锛屽彲鍏宠仈鍙戠エ锛屼篃鏀寔鍏堟敹娆惧悗寮€绁ㄣ€? : '璁板綍椤圭洰寮€绁ㄦ儏鍐碉紝鍙寜璐︽湡銆佸悎鍚屻€佹潵婧愬崟鍙锋牳瀵广€? }}</p>
      </div>
      <el-button type="success" :icon="Plus" @click="openCreate">鏂板{{ isReceipt ? '鏀舵' : '鍙戠エ' }}</el-button>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="鎼滅储鍗曞彿銆佸鎴枫€佽处鏈熴€佹潵婧? @keyup.enter="loadRows" @clear="loadRows" />
        <el-button type="success" plain :icon="Search" @click="loadRows">鏌ヨ</el-button>
        <el-button :icon="Refresh" @click="keyword=''; loadRows()">閲嶇疆</el-button>
      </div>
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column :prop="meta.noKey" :label="meta.noLabel" min-width="135" fixed />
        <el-table-column prop="project_name" label="椤圭洰" min-width="170" />
        <el-table-column prop="contract_name" label="鍚堝悓" min-width="150" show-overflow-tooltip />
        <el-table-column :prop="meta.dateKey" :label="isReceipt ? '鏀舵鏃ユ湡' : '寮€绁ㄦ棩鏈?" width="110" />
        <el-table-column prop="billing_period" label="璐︽湡" width="105" />
        <el-table-column label="閲戦" width="115"><template #default="scope">{{ formatMoney(scope.row.amount) }}</template></el-table-column>
        <el-table-column v-if="!isReceipt" label="绋庨" width="95"><template #default="scope">{{ formatMoney(scope.row.tax_amount) }}</template></el-table-column>
        <el-table-column v-if="!isReceipt" prop="invoice_type" label="鍙戠エ绫诲瀷" width="105" />
        <el-table-column v-if="isReceipt" prop="payment_method" label="鏀舵鏂瑰紡" width="105" />
        <el-table-column v-if="isReceipt" prop="invoice_no" label="鍏宠仈鍙戠エ" min-width="130" />
        <el-table-column prop="payer_name" label="浠樻鏂? min-width="140" />
        <el-table-column prop="handler" label="缁忔墜浜? width="95" />
        <el-table-column prop="source_no" label="鏉ユ簮鍗曞彿" min-width="130" />
        <el-table-column label="鐘舵€? width="90"><template #default="scope"><el-tag :type="scope.row.status?.includes('浣滃簾') ? 'info' : 'success'" size="small">{{ scope.row.status }}</el-tag></template></el-table-column>
        <el-table-column prop="notes" label="澶囨敞" min-width="160" show-overflow-tooltip />
        <el-table-column label="鎿嶄綔" width="95">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="openEdit(scope.row)">缂栬緫</el-dropdown-item>
                  <el-dropdown-item divided @click="deleteRecord(scope.row)">鍒犻櫎</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <el-dialog v-model="dialogVisible" :title="`${editingId ? '缂栬緫' : '鏂板'}${meta.title}`" width="760px" destroy-on-close>
      <el-form label-position="top">
        <div class="form-grid two">
          <el-form-item :label="meta.noLabel" required><el-input v-model="form[meta.noKey]" /></el-form-item>
          <el-form-item label="椤圭洰" required>
            <el-select v-model="form.project_id" filterable style="width:100%">
              <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
            </el-select>
          </el-form-item>
          <el-form-item :label="isReceipt ? '鏀舵鏃ユ湡' : '寮€绁ㄦ棩鏈?" required><el-date-picker v-model="form[meta.dateKey]" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
          <el-form-item label="璐︽湡"><el-input v-model="form.billing_period" placeholder="渚嬪锛?026-08銆?026骞寸涓夊搴︺€?-9鏈? /></el-form-item>
          <el-form-item :label="meta.amountLabel" required><el-input-number v-model="form.amount" :min="0" :controls="false" style="width:100%" /></el-form-item>
          <el-form-item v-if="!isReceipt" label="绋庨"><el-input-number v-model="form.tax_amount" :min="0" :controls="false" style="width:100%" /></el-form-item>
          <el-form-item v-if="!isReceipt" label="鍙戠エ绫诲瀷">
            <el-select v-model="form.invoice_type" allow-create filterable style="width:100%">
              <el-option label="鏅€氬彂绁? value="鏅€氬彂绁? />
              <el-option label="涓撶敤鍙戠エ" value="涓撶敤鍙戠エ" />
              <el-option label="鐢靛瓙鍙戠エ" value="鐢靛瓙鍙戠エ" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="isReceipt" label="鍏宠仈鍙戠エ">
            <el-select v-model="form.invoice_id" clearable filterable style="width:100%">
              <el-option v-for="invoice in invoices" :key="invoice.id" :label="`${invoice.invoice_no}锝?{invoice.project_name}锝?{formatMoney(invoice.amount)}`" :value="invoice.id" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="isReceipt" label="鏀舵鏂瑰紡">
            <el-select v-model="form.payment_method" allow-create filterable style="width:100%">
              <el-option label="閾惰杞处" value="閾惰杞处" />
              <el-option label="寰俊" value="寰俊" />
              <el-option label="鏀粯瀹? value="鏀粯瀹? />
              <el-option label="鐜伴噾" value="鐜伴噾" />
            </el-select>
          </el-form-item>
          <el-form-item label="浠樻鏂?><el-input v-model="form.payer_name" /></el-form-item>
          <el-form-item label="缁忔墜浜?><el-input v-model="form.handler" /></el-form-item>
          <el-form-item label="鏉ユ簮鍗曞彿"><el-input v-model="form.source_no" placeholder="鍙～璁㈠崟鍙枫€佸悎鍚岀紪鍙枫€侀摱琛屾祦姘村彿绛? /></el-form-item>
          <el-form-item label="鐘舵€?>
            <el-select v-model="form.status" style="width:100%">
              <el-option :label="isReceipt ? '宸叉敹娆? : '宸插紑绁?" :value="isReceipt ? '宸叉敹娆? : '宸插紑绁?" />
              <el-option label="寰呯‘璁? value="寰呯‘璁? />
              <el-option label="浣滃簾" value="浣滃簾" />
            </el-select>
          </el-form-item>
          <el-form-item label="澶囨敞" class="wide"><el-input v-model="form.notes" type="textarea" :rows="3" /></el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">鍙栨秷</el-button>
        <el-button type="success" :loading="saving" @click="saveRecord">淇濆瓨</el-button>
      </template>
    </el-dialog>
  </div>
</template>

