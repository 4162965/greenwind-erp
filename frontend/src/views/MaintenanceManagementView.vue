<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ArrowDown, Calendar, Delete, Edit, Plus, Refresh, Search, Tickets, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const activeTab = ref('plans')
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const recordKeyword = ref('')
const plans = ref<Row[]>([])
const records = ref<Row[]>([])
const projects = ref<Row[]>([])
const employees = ref<Row[]>([])
const planDialog = ref(false)
const recordDialog = ref(false)
const orderDialog = ref(false)
const editingPlanId = ref<number | null>(null)
const selectedRecord = ref<Row | null>(null)
const recordPhotoInput = ref<HTMLInputElement>()
const recordPhotos = ref<Row[]>([])
const planForm = reactive<Row>({})
const recordForm = reactive<Row>({})
const orderForm = reactive<Row>({ action_type: '鎹㈣姳璁㈠崟', need_purchase: true, need_delivery: true })

const activePlanCount = computed(() => plans.value.filter((row) => row.status === '鍚敤').length)
const duePlanCount = computed(() => plans.value.filter((row) => row.next_due_date && row.status === '鍚敤').length)
const generatedOrderCount = computed(() => records.value.filter((row) => row.generated_order_no).length)

function today() {
  return new Date().toISOString().slice(0, 10)
}

function resetObject(target: Row, values: Row) {
  Object.keys(target).forEach((key) => delete target[key])
  Object.assign(target, values)
}

function fileToDataUrl(file: File, done: (url: string) => void) {
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.warning(`${file.name}瓒呰繃5MB锛岃鍘嬬缉鍚庝笂浼燻)
    return
  }
  const reader = new FileReader()
  reader.onload = () => done(String(reader.result))
  reader.readAsDataURL(file)
}

function chooseRecordPhotos() {
  recordPhotoInput.value?.click()
}

function handleRecordPhotos(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (recordPhotos.value.length + files.length > 9) {
    ElMessage.warning('涓€娆″吇鎶よ褰曟渶澶氫笂浼?寮犵幇鍦虹収鐗?)
    input.value = ''
    return
  }
  files.forEach((file) => {
    fileToDataUrl(file, (url) => {
      recordPhotos.value.push({ file_name: file.name, file_type: file.type || 'image/*', file_size: file.size, data_url: url })
    })
  })
  input.value = ''
}

function statusTag(status: string) {
  if (status === '鍚敤' || status === '宸插畬鎴?) return 'success'
  if (status === '鍋滅敤' || status === '宸插彇娑?) return 'info'
  if (status === '鑽夌') return 'warning'
  return ''
}

async function loadOptions() {
  const [projectRes, employeeRes] = await Promise.all([
    api.get('/projects'),
    api.get('/employees', { params: { keyword: '' } }),
  ])
  projects.value = projectRes.data.items || []
  employees.value = employeeRes.data.items || []
}

async function loadPlans() {
  loading.value = true
  try {
    plans.value = (await api.get('/maintenance/plans', { params: { keyword: keyword.value.trim() } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鍏绘姢璁″垝鍔犺浇澶辫触')
  } finally {
    loading.value = false
  }
}

async function loadRecords() {
  loading.value = true
  try {
    records.value = (await api.get('/maintenance/records', { params: { keyword: recordKeyword.value.trim() } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鍏绘姢璁板綍鍔犺浇澶辫触')
  } finally {
    loading.value = false
  }
}

async function openCreatePlan() {
  await loadOptions()
  editingPlanId.value = null
  resetObject(planForm, {
    project_id: null,
    maintainer_id: null,
    area_description: '鍏ㄩ儴鍖哄煙',
    frequency_type: '姣忔湀娆℃暟',
    frequency_value: '4娆?鏈?,
    service_content: '娴囨按銆佷慨鍓€佹竻鐞嗛粍鍙躲€佹鏌ユ鐗╃姸鎬?,
    start_date: today(),
    end_date: null,
    next_due_date: today(),
    reminder_days: 2,
    status: '鍚敤',
    notes: '',
  })
  planDialog.value = true
}

async function openEditPlan(row: Row) {
  await loadOptions()
  editingPlanId.value = row.id
  resetObject(planForm, { ...row })
  planDialog.value = true
}

async function savePlan() {
  if (!planForm.project_id) {
    ElMessage.warning('璇烽€夋嫨椤圭洰')
    return
  }
  saving.value = true
  try {
    if (editingPlanId.value) await api.put(`/maintenance/plans/${editingPlanId.value}`, planForm)
    else await api.post('/maintenance/plans', planForm)
    ElMessage.success(`鍏绘姢璁″垝宸?{editingPlanId.value ? '淇敼' : '鏂板'}`)
    planDialog.value = false
    await loadPlans()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鍏绘姢璁″垝淇濆瓨澶辫触')
  } finally {
    saving.value = false
  }
}

async function openCreateRecord(plan?: Row) {
  await loadOptions()
  recordPhotos.value = []
  resetObject(recordForm, {
    plan_id: plan?.id || null,
    project_id: plan?.project_id || null,
    maintainer_id: plan?.maintainer_id || null,
    service_date: today(),
    area_description: plan?.area_description || '',
    work_content: plan?.service_content || '',
    site_issue: '',
    handle_result: '',
    photos: '',
    customer_feedback: '',
    next_plan_date: '',
    status: '宸插畬鎴?,
    notes: '',
  })
  recordDialog.value = true
}

async function saveRecord() {
  if (!recordForm.project_id && !recordForm.plan_id) {
    ElMessage.warning('璇烽€夋嫨椤圭洰鎴栧吇鎶よ鍒?)
    return
  }
  saving.value = true
  try {
    recordForm.photos = recordPhotos.value.map((item) => item.file_name).join('锛?) || recordForm.photos
    const response = await api.post('/maintenance/records', recordForm)
    const record = response.data
    for (const photo of recordPhotos.value) {
      await api.post('/attachments', {
        target_type: '鍏绘姢鐓х墖',
        target_id: record.id,
        target_name: `${record.record_no}锝?{record.project_name || ''}`,
        file_name: photo.file_name,
        file_type: photo.file_type,
        file_size: photo.file_size,
        data_url: photo.data_url,
        notes: recordForm.area_description || '',
      })
    }
    ElMessage.success(recordPhotos.value.length ? `鍏绘姢璁板綍宸蹭繚瀛橈紝骞朵笂浼?{recordPhotos.value.length}寮犵収鐗嘸 : '鍏绘姢璁板綍宸蹭繚瀛?)
    recordDialog.value = false
    await Promise.all([loadRecords(), loadPlans()])
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鍏绘姢璁板綍淇濆瓨澶辫触')
  } finally {
    saving.value = false
  }
}

function openCreateOrder(row: Row) {
  selectedRecord.value = row
  resetObject(orderForm, {
    action_type: '鎹㈣姳璁㈠崟',
    expected_date: today(),
    priority: '鏅€?,
    need_purchase: true,
    need_delivery: true,
  })
  orderDialog.value = true
}

async function createOrder() {
  if (!selectedRecord.value) return
  saving.value = true
  try {
    const response = await api.post(`/maintenance/records/${selectedRecord.value.id}/create-order`, orderForm)
    ElMessage.success(response.data.status === 'exists' ? `璁㈠崟宸插瓨鍦細${response.data.order_no}` : `宸茬敓鎴愯鍗曪細${response.data.order_no}`)
    orderDialog.value = false
    await loadRecords()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鐢熸垚璁㈠崟澶辫触')
  } finally {
    saving.value = false
  }
}

loadOptions()
loadPlans()
loadRecords()
</script>

<template>
  <div class="page maintenance-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">MAINTENANCE</p>
        <h1>鍏绘姢绠＄悊</h1>
        <p>寤虹珛椤圭洰鍏绘姢璁″垝锛岃褰曠幇鍦哄吇鎶ゆ儏鍐碉紝骞跺彲浠庡吇鎶よ褰曠洿鎺ョ敓鎴愭崲鑺辨垨鏈嶅姟璁㈠崟銆?/p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreatePlan">鏂板鍏绘姢璁″垝</el-button>
    </div>

    <div class="inventory-summary maintenance-summary">
      <div><span>鍏绘姢璁″垝</span><strong>{{ plans.length }}</strong></div>
      <div><span>鍚敤涓?/span><strong>{{ activePlanCount }}</strong></div>
      <div><span>寰呰窡杩涜鍒?/span><strong>{{ duePlanCount }}</strong></div>
      <div><span>宸茶浆璁㈠崟璁板綍</span><strong>{{ generatedOrderCount }}</strong></div>
    </div>

    <article class="panel table-panel maintenance-panel">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="鍏绘姢璁″垝" name="plans">
          <div class="table-toolbar">
            <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="鎼滅储璁″垝缂栧彿銆侀」鐩€佸尯鍩熴€佸唴瀹? @keyup.enter="loadPlans" @clear="loadPlans" />
            <el-button type="success" plain :icon="Search" @click="loadPlans">鏌ヨ</el-button>
            <el-button :icon="Refresh" @click="keyword=''; loadPlans()">閲嶇疆</el-button>
          </div>
          <el-table v-loading="loading" :data="plans" stripe>
            <el-table-column prop="plan_no" label="璁″垝缂栧彿" min-width="130" />
            <el-table-column prop="project_name" label="椤圭洰" min-width="170" />
            <el-table-column prop="maintainer_name" label="鍏绘姢鍛? width="100" />
            <el-table-column prop="area_description" label="璐熻矗鍖哄煙" min-width="140" show-overflow-tooltip />
            <el-table-column label="棰戠巼" min-width="130"><template #default="scope">{{ scope.row.frequency_type }} {{ scope.row.frequency_value }}</template></el-table-column>
            <el-table-column prop="service_content" label="鍏绘姢鍐呭" min-width="220" show-overflow-tooltip />
            <el-table-column prop="next_due_date" label="涓嬫璁″垝" width="110" />
            <el-table-column label="鐘舵€? width="90"><template #default="scope"><el-tag :type="statusTag(scope.row.status)">{{ scope.row.status }}</el-tag></template></el-table-column>
            <el-table-column label="鎿嶄綔" width="95">
              <template #default="scope">
                <el-dropdown trigger="click">
                  <el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item :icon="Edit" @click="openEditPlan(scope.row)">缂栬緫</el-dropdown-item>
                      <el-dropdown-item :icon="Tickets" @click="openCreateRecord(scope.row)">鍐欒褰?/el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="鍏绘姢璁板綍" name="records">
          <div class="table-toolbar">
            <el-input v-model="recordKeyword" clearable :prefix-icon="Search" placeholder="鎼滅储璁板綍缂栧彿銆侀」鐩€佸唴瀹广€侀棶棰? @keyup.enter="loadRecords" @clear="loadRecords" />
            <el-button type="success" plain :icon="Search" @click="loadRecords">鏌ヨ</el-button>
            <el-button :icon="Refresh" @click="recordKeyword=''; loadRecords()">閲嶇疆</el-button>
            <el-button type="success" :icon="Plus" @click="openCreateRecord()">鏂板璁板綍</el-button>
          </div>
          <el-table v-loading="loading" :data="records" stripe>
            <el-table-column prop="record_no" label="璁板綍缂栧彿" min-width="130" />
            <el-table-column prop="service_date" label="鏃ユ湡" width="110" />
            <el-table-column prop="project_name" label="椤圭洰" min-width="160" />
            <el-table-column prop="maintainer_name" label="鍏绘姢鍛? width="100" />
            <el-table-column prop="area_description" label="鍖哄煙" min-width="130" show-overflow-tooltip />
            <el-table-column prop="work_content" label="宸ヤ綔鍐呭" min-width="220" show-overflow-tooltip />
            <el-table-column prop="site_issue" label="鐜板満闂" min-width="180" show-overflow-tooltip />
            <el-table-column prop="handle_result" label="澶勭悊缁撴灉/寤鸿" min-width="190" show-overflow-tooltip />
            <el-table-column prop="generated_order_no" label="鍏宠仈璁㈠崟" min-width="130" />
            <el-table-column label="鐘舵€? width="90"><template #default="scope"><el-tag :type="statusTag(scope.row.status)">{{ scope.row.status }}</el-tag></template></el-table-column>
            <el-table-column label="鎿嶄綔" width="95">
              <template #default="scope">
                <el-dropdown trigger="click">
                  <el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item :icon="Calendar" :disabled="Boolean(scope.row.generated_order_no)" @click="openCreateOrder(scope.row)">鐢熸垚璁㈠崟</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </article>

    <el-dialog v-model="planDialog" :title="`${editingPlanId ? '缂栬緫' : '鏂板'}鍏绘姢璁″垝`" width="860px" destroy-on-close>
      <el-form label-position="top">
        <div class="form-grid three">
          <el-form-item label="椤圭洰" required><el-select v-model="planForm.project_id" filterable style="width:100%"><el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" /></el-select></el-form-item>
          <el-form-item label="鍏绘姢鍛?><el-select v-model="planForm.maintainer_id" clearable filterable style="width:100%"><el-option v-for="employee in employees" :key="employee.id" :label="employee.name" :value="employee.id" /></el-select></el-form-item>
          <el-form-item label="鐘舵€?><el-select v-model="planForm.status" style="width:100%"><el-option label="鍚敤" value="鍚敤" /><el-option label="鍋滅敤" value="鍋滅敤" /></el-select></el-form-item>
          <el-form-item label="璐熻矗鍖哄煙"><el-input v-model="planForm.area_description" /></el-form-item>
          <el-form-item label="棰戠巼绫诲瀷"><el-select v-model="planForm.frequency_type" style="width:100%"><el-option label="姣忓懆鍥哄畾" value="姣忓懆鍥哄畾" /><el-option label="姣忔湀娆℃暟" value="姣忔湀娆℃暟" /><el-option label="涓存椂璁″垝" value="涓存椂璁″垝" /></el-select></el-form-item>
          <el-form-item label="棰戠巼璇存槑"><el-input v-model="planForm.frequency_value" placeholder="渚嬪锛氭瘡鍛ㄤ簩銆佹瘡鏈?娆? /></el-form-item>
          <el-form-item label="寮€濮嬫棩鏈?><el-date-picker v-model="planForm.start_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
          <el-form-item label="缁撴潫鏃ユ湡"><el-date-picker v-model="planForm.end_date" value-format="YYYY-MM-DD" clearable style="width:100%" /></el-form-item>
          <el-form-item label="涓嬫璁″垝鏃ユ湡"><el-date-picker v-model="planForm.next_due_date" value-format="YYYY-MM-DD" clearable style="width:100%" /></el-form-item>
          <el-form-item label="鍏绘姢鍐呭" class="wide"><el-input v-model="planForm.service_content" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="澶囨敞" class="wide"><el-input v-model="planForm.notes" type="textarea" :rows="2" /></el-form-item>
        </div>
      </el-form>
      <template #footer><el-button @click="planDialog=false">鍙栨秷</el-button><el-button type="success" :loading="saving" @click="savePlan">淇濆瓨</el-button></template>
    </el-dialog>

    <el-dialog v-model="recordDialog" title="鏂板鍏绘姢璁板綍" width="900px" destroy-on-close>
      <el-form label-position="top">
        <div class="form-grid three">
          <el-form-item label="鍏宠仈璁″垝"><el-select v-model="recordForm.plan_id" clearable filterable style="width:100%"><el-option v-for="plan in plans" :key="plan.id" :label="`${plan.plan_no}锝?{plan.project_name}`" :value="plan.id" /></el-select></el-form-item>
          <el-form-item label="椤圭洰"><el-select v-model="recordForm.project_id" clearable filterable style="width:100%"><el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" /></el-select></el-form-item>
          <el-form-item label="鍏绘姢鍛?><el-select v-model="recordForm.maintainer_id" clearable filterable style="width:100%"><el-option v-for="employee in employees" :key="employee.id" :label="employee.name" :value="employee.id" /></el-select></el-form-item>
          <el-form-item label="鍏绘姢鏃ユ湡"><el-date-picker v-model="recordForm.service_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
          <el-form-item label="鍖哄煙"><el-input v-model="recordForm.area_description" /></el-form-item>
          <el-form-item label="涓嬫璁″垝"><el-date-picker v-model="recordForm.next_plan_date" value-format="YYYY-MM-DD" clearable style="width:100%" /></el-form-item>
          <el-form-item label="宸ヤ綔鍐呭" class="wide"><el-input v-model="recordForm.work_content" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="鐜板満闂" class="wide"><el-input v-model="recordForm.site_issue" type="textarea" :rows="3" placeholder="渚嬪锛氱豢钀濈姸鎬佸樊銆佺泦鐮存崯銆侀渶瑕佷慨鍓墦鑽? /></el-form-item>
          <el-form-item label="澶勭悊缁撴灉/寤鸿" class="wide"><el-input v-model="recordForm.handle_result" type="textarea" :rows="3" placeholder="鍙啓锛氬缓璁崲鑺便€佹崲鐩嗐€侀噰璐嵂鍝併€佸鎴疯嚜琛屽鐞嗙瓑" /></el-form-item>
          <el-form-item label="鐜板満鐓х墖" class="wide">
            <div class="record-photo-uploader">
              <input ref="recordPhotoInput" class="hidden-input" type="file" accept="image/*" multiple @change="handleRecordPhotos" />
              <button type="button" class="record-photo-add" @click="chooseRecordPhotos">
                <el-icon><UploadFilled /></el-icon>
                <span>涓婁紶鐜板満鐓х墖</span>
                <small>鏈€澶?寮狅紝淇濆瓨鍚庤嚜鍔ㄨ繘鍏ラ檮浠朵腑蹇?/small>
              </button>
              <div v-for="(photo,index) in recordPhotos" :key="`${photo.file_name}-${index}`" class="record-photo-card">
                <el-image :src="photo.data_url" fit="cover" />
                <button type="button" @click="recordPhotos.splice(index,1)"><el-icon><Delete /></el-icon></button>
                <span>{{ photo.file_name }}</span>
              </div>
            </div>
          </el-form-item>
          <el-form-item label="瀹㈡埛澶囨敞" class="wide"><el-input v-model="recordForm.customer_feedback" type="textarea" :rows="2" /></el-form-item>
        </div>
      </el-form>
      <template #footer><el-button @click="recordDialog=false">鍙栨秷</el-button><el-button type="success" :loading="saving" @click="saveRecord">淇濆瓨璁板綍</el-button></template>
    </el-dialog>

    <el-dialog v-model="orderDialog" title="鐢卞吇鎶よ褰曠敓鎴愯鍗? width="560px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="鐢熸垚璁㈠崟绫诲瀷"><el-select v-model="orderForm.action_type" style="width:100%"><el-option label="鎹㈣姳璁㈠崟" value="鎹㈣姳璁㈠崟" /><el-option label="鍏绘姢璁㈠崟" value="鍏绘姢璁㈠崟" /><el-option label="鎾よ姳璁㈠崟" value="鎾よ姳璁㈠崟" /></el-select></el-form-item>
        <el-form-item label="鏈熸湜瀹屾垚鏃ユ湡"><el-date-picker v-model="orderForm.expected_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="浼樺厛绾?><el-select v-model="orderForm.priority" style="width:100%"><el-option label="鏅€? value="鏅€? /><el-option label="绱ф€? value="绱ф€? /></el-select></el-form-item>
        <el-form-item label="娴佺▼闇€瑕?><el-checkbox v-model="orderForm.need_purchase">闇€瑕侀噰璐?/el-checkbox><el-checkbox v-model="orderForm.need_delivery">闇€瑕侀厤閫?瀹夋帓</el-checkbox></el-form-item>
      </el-form>
      <template #footer><el-button @click="orderDialog=false">鍙栨秷</el-button><el-button type="success" :loading="saving" @click="createOrder">鐢熸垚璁㈠崟</el-button></template>
    </el-dialog>
  </div>
</template>

