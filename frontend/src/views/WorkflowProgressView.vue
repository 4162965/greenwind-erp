<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ArrowDown, Check, Close, Delete, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const activeTab = ref('requests')
const loading = ref(false)
const ruleLoading = ref(false)
const saving = ref(false)
const keyword = ref('')
const statusFilter = ref('')
const ruleKeyword = ref('')
const requests = ref<Row[]>([])
const rules = ref<Row[]>([])
const projects = ref<Row[]>([])
const dialogVisible = ref(false)
const editingRuleId = ref<number | null>(null)
const decisionVisible = ref(false)
const selectedRequest = ref<Row | null>(null)
const ruleForm = reactive<Row>({})
const decisionForm = reactive({ status: '宸查€氳繃', decision_comment: '' })

function resetRule(values: Row) {
  Object.keys(ruleForm).forEach((key) => delete ruleForm[key])
  Object.assign(ruleForm, values)
}

function emptyRule() {
  return {
    project_id: null,
    purchase_requires_approval: false,
    exchange_annual_limit: null,
    approver_role: '缁忕悊',
    approver_name: '',
    status: '鍚敤',
    notes: '',
  }
}

function statusTag(status: string) {
  if (status === '宸查€氳繃') return 'success'
  if (status === '宸查┏鍥?) return 'danger'
  if (status === '寰呭鎵?) return 'warning'
  return 'info'
}

function formatMoney(value: number | string | null | undefined) {
  const number = Number(value || 0)
  if (!number) return '鈥?
  return `楼${Number.isInteger(number) ? number : number.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')}`
}

async function loadProjects() {
  projects.value = (await api.get('/projects')).data.items
}

async function loadRequests() {
  loading.value = true
  try {
    requests.value = (await api.get('/workflows/requests', { params: { keyword: keyword.value.trim(), status: statusFilter.value } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '瀹℃壒璁板綍鍔犺浇澶辫触')
  } finally {
    loading.value = false
  }
}

async function loadRules() {
  ruleLoading.value = true
  try {
    rules.value = (await api.get('/workflows/rules', { params: { keyword: ruleKeyword.value.trim() } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '瀹℃壒瑙勫垯鍔犺浇澶辫触')
  } finally {
    ruleLoading.value = false
  }
}

async function openCreateRule() {
  editingRuleId.value = null
  await loadProjects()
  resetRule(emptyRule())
  dialogVisible.value = true
}

async function openEditRule(row: Row) {
  editingRuleId.value = row.id
  await loadProjects()
  resetRule({ ...row })
  dialogVisible.value = true
}

async function saveRule() {
  if (!ruleForm.project_id) {
    ElMessage.warning('璇烽€夋嫨椤圭洰')
    return
  }
  saving.value = true
  try {
    const payload = { ...ruleForm, exchange_annual_limit: Number(ruleForm.exchange_annual_limit || 0) }
    if (editingRuleId.value) await api.put(`/workflows/rules/${editingRuleId.value}`, payload)
    else await api.post('/workflows/rules', payload)
    ElMessage.success(`瀹℃壒瑙勫垯宸?{editingRuleId.value ? '淇敼' : '鏂板'}`)
    dialogVisible.value = false
    await loadRules()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '瀹℃壒瑙勫垯淇濆瓨澶辫触')
  } finally {
    saving.value = false
  }
}

async function deleteRule(row: Row) {
  await ElMessageBox.confirm(`纭鍒犻櫎鈥?{row.project_name}鈥濈殑瀹℃壒瑙勫垯鍚楋紵`, '鍒犻櫎瀹℃壒瑙勫垯', { type: 'warning' })
  try {
    await api.delete(`/workflows/rules/${row.id}`)
    ElMessage.success('瀹℃壒瑙勫垯宸插垹闄?)
    await loadRules()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '瀹℃壒瑙勫垯鍒犻櫎澶辫触')
  }
}

function openDecision(row: Row, status: string) {
  selectedRequest.value = row
  decisionForm.status = status
  decisionForm.decision_comment = ''
  decisionVisible.value = true
}

async function saveDecision() {
  if (!selectedRequest.value) return
  saving.value = true
  try {
    await api.post(`/workflows/requests/${selectedRequest.value.id}/decision`, decisionForm)
    ElMessage.success(`瀹℃壒宸?{decisionForm.status === '宸查€氳繃' ? '閫氳繃' : '椹冲洖'}`)
    decisionVisible.value = false
    await loadRequests()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '瀹℃壒澶勭悊澶辫触')
  } finally {
    saving.value = false
  }
}

loadProjects()
loadRequests()
loadRules()
</script>

<template>
  <div class="page workflow-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">WORKFLOW</p>
        <h1>瀹℃壒杩涘害</h1>
        <p>鍏堝缓绔嬮」鐩鎵硅鍒欙紱璁㈠崟瑙﹀彂瑙勫垯鍚庝細杩涘叆寰呭鎵癸紝閫氳繃鍚庤鍗曞洖鍒板緟澶勭悊锛岄┏鍥炲悗璁㈠崟鍙樹负宸查┏鍥炪€?/p>
      </div>
    </div>

    <article class="panel table-panel">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="瀹℃壒璁板綍" name="requests">
          <div class="table-toolbar">
            <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="鎼滅储瀹℃壒鍗曞彿銆佹潵婧愬崟鍙枫€侀」鐩€佸師鍥? @keyup.enter="loadRequests" @clear="loadRequests" />
            <el-select v-model="statusFilter" clearable placeholder="瀹℃壒鐘舵€? @change="loadRequests">
              <el-option label="寰呭鎵? value="寰呭鎵? />
              <el-option label="宸查€氳繃" value="宸查€氳繃" />
              <el-option label="宸查┏鍥? value="宸查┏鍥? />
            </el-select>
            <el-button type="success" plain :icon="Search" @click="loadRequests">鏌ヨ</el-button>
            <el-button :icon="Refresh" @click="keyword=''; statusFilter=''; loadRequests()">閲嶇疆</el-button>
          </div>

          <el-table v-loading="loading" :data="requests" stripe>
            <el-table-column prop="request_no" label="瀹℃壒鍗曞彿" min-width="130" />
            <el-table-column prop="approval_type" label="绫诲瀷" width="105" />
            <el-table-column prop="project_name" label="椤圭洰" min-width="150" />
            <el-table-column label="鏉ユ簮" min-width="135"><template #default="scope">{{ [scope.row.source_type, scope.row.source_no].filter(Boolean).join('锛?) }}</template></el-table-column>
            <el-table-column prop="applicant" label="鐢宠浜? width="95" />
            <el-table-column label="閲戦" width="105"><template #default="scope">{{ formatMoney(scope.row.amount) }}</template></el-table-column>
            <el-table-column prop="reason" label="瑙﹀彂鍘熷洜" min-width="230" show-overflow-tooltip />
            <el-table-column label="瀹℃壒浜? min-width="130"><template #default="scope">{{ scope.row.approver_name || scope.row.approver_role }}</template></el-table-column>
            <el-table-column label="鐘舵€? width="95"><template #default="scope"><el-tag :type="statusTag(scope.row.status)">{{ scope.row.status }}</el-tag></template></el-table-column>
            <el-table-column prop="decision_comment" label="瀹℃壒鎰忚" min-width="160" show-overflow-tooltip />
            <el-table-column label="鎿嶄綔" width="135">
              <template #default="scope">
                <el-button v-if="scope.row.status === '寰呭鎵?" link type="success" :icon="Check" @click="openDecision(scope.row, '宸查€氳繃')">閫氳繃</el-button>
                <el-button v-if="scope.row.status === '寰呭鎵?" link type="danger" :icon="Close" @click="openDecision(scope.row, '宸查┏鍥?)">椹冲洖</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="瀹℃壒瑙勫垯" name="rules">
          <div class="table-toolbar">
            <el-input v-model="ruleKeyword" clearable :prefix-icon="Search" placeholder="鎼滅储椤圭洰鎴栧鎵逛汉" @keyup.enter="loadRules" @clear="loadRules" />
            <el-button type="success" plain :icon="Search" @click="loadRules">鏌ヨ</el-button>
            <el-button :icon="Refresh" @click="ruleKeyword=''; loadRules()">閲嶇疆</el-button>
            <el-button type="success" :icon="Plus" @click="openCreateRule">鏂板瑙勫垯</el-button>
          </div>

          <el-table v-loading="ruleLoading" :data="rules" stripe>
            <el-table-column prop="project_name" label="椤圭洰" min-width="180" />
            <el-table-column label="閲囪喘闇€姹傚鎵? width="125"><template #default="scope"><el-tag :type="scope.row.purchase_requires_approval ? 'warning' : 'info'">{{ scope.row.purchase_requires_approval ? '闇€瑕? : '涓嶉渶瑕? }}</el-tag></template></el-table-column>
            <el-table-column label="鎹㈣姳骞村害棰濆害" width="130"><template #default="scope">{{ formatMoney(scope.row.exchange_annual_limit) }}</template></el-table-column>
            <el-table-column label="瀹℃壒浜? min-width="135"><template #default="scope">{{ scope.row.approver_name || scope.row.approver_role }}</template></el-table-column>
            <el-table-column label="鐘舵€? width="85"><template #default="scope"><el-tag :type="scope.row.status === '鍚敤' ? 'success' : 'info'">{{ scope.row.status }}</el-tag></template></el-table-column>
            <el-table-column prop="notes" label="澶囨敞" min-width="180" show-overflow-tooltip />
            <el-table-column label="鎿嶄綔" width="95">
              <template #default="scope">
                <el-dropdown trigger="click">
                  <el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item @click="openEditRule(scope.row)">缂栬緫</el-dropdown-item>
                      <el-dropdown-item divided @click="deleteRule(scope.row)">鍒犻櫎</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </article>

    <el-dialog v-model="dialogVisible" :title="`${editingRuleId ? '缂栬緫' : '鏂板'}瀹℃壒瑙勫垯`" width="720px" destroy-on-close>
      <el-form label-position="top">
        <div class="form-grid two">
          <el-form-item label="椤圭洰" required>
            <el-select v-model="ruleForm.project_id" filterable style="width:100%" :disabled="Boolean(editingRuleId)">
              <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="鐘舵€?>
            <el-select v-model="ruleForm.status" style="width:100%">
              <el-option label="鍚敤" value="鍚敤" />
              <el-option label="鍋滅敤" value="鍋滅敤" />
            </el-select>
          </el-form-item>
          <el-form-item label="閲囪喘闇€姹傛槸鍚﹀繀椤诲鎵?><el-switch v-model="ruleForm.purchase_requires_approval" active-text="闇€瑕? inactive-text="涓嶉渶瑕? /></el-form-item>
          <el-form-item label="鎹㈣姳骞村害绱瓒呰繃澶氬皯瀹℃壒">
            <el-input-number v-model="ruleForm.exchange_annual_limit" :min="0" :controls="false" style="width:100%" />
            <small class="form-hint">濉?0 琛ㄧず涓嶆寜鎹㈣姳閲戦瑙﹀彂銆?/small>
          </el-form-item>
          <el-form-item label="瀹℃壒瑙掕壊"><el-input v-model="ruleForm.approver_role" placeholder="渚嬪锛氱粡鐞嗐€佷富绠°€佽€佹澘" /></el-form-item>
          <el-form-item label="鎸囧畾瀹℃壒浜?><el-input v-model="ruleForm.approver_name" placeholder="鍙┖锛涘悗闈細鎺ュ憳宸ラ€夋嫨" /></el-form-item>
          <el-form-item label="澶囨敞" class="wide"><el-input v-model="ruleForm.notes" type="textarea" :rows="3" /></el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">鍙栨秷</el-button>
        <el-button type="success" :loading="saving" @click="saveRule">淇濆瓨瑙勫垯</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="decisionVisible" :title="decisionForm.status === '宸查€氳繃' ? '閫氳繃瀹℃壒' : '椹冲洖瀹℃壒'" width="520px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="瀹℃壒鎰忚">
          <el-input v-model="decisionForm.decision_comment" type="textarea" :rows="4" placeholder="鍙～鍐欏師鍥犳垨琛ュ厖璇存槑" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="decisionVisible=false">鍙栨秷</el-button>
        <el-button :type="decisionForm.status === '宸查€氳繃' ? 'success' : 'danger'" :loading="saving" @click="saveDecision">{{ decisionForm.status === '宸查€氳繃' ? '纭閫氳繃' : '纭椹冲洖' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

