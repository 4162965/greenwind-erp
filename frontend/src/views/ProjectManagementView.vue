<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDown, Edit, Plus, Refresh, Search, View } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>
type DetailType = 'contact' | 'location' | 'maintainer' | 'contract' | 'plant' | 'salary'

const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const projects = ref<Row[]>([])
const customers = ref<Row[]>([])
const employees = ref<Row[]>([])
const products = ref<Row[]>([])
const selectedProject = ref<Row | null>(null)
const projectDialog = ref(false)
const projectEditingId = ref<number | null>(null)
const detailVisible = ref(false)
const activeTab = ref('locations')
const subDialog = ref(false)
const subType = ref<DetailType>('contact')
const subEditingId = ref<number | null>(null)
const plantChangeDialog = ref(false)
const selectedPlant = ref<Row | null>(null)
const plantChanges = ref<Row[]>([])

const detail = reactive<Record<string, Row[]>>({
  contacts: [], locations: [], maintainers: [], contracts: [], plants: [], salaries: [],
})
const projectForm = reactive<Row>({})
const subForm = reactive<Row>({})
const route = useRoute()

const businessOptions = ['租摆', '工程绿化', '电网', '保洁']
const currentBusiness = computed(() => String(route.query.business || '租摆'))
const pageTitle = computed(() => `${currentBusiness.value}项目管理`)
const supervisorOptions = computed(() => employees.value.filter((item) => ['主管', '经理'].some((role) => `${item.position},${item.role},${item.business_roles}`.includes(role))))
const maintainerOptions = computed(() => employees.value.filter((item) => `${item.position},${item.role},${item.business_roles}`.includes('养护')))
const customerServiceOptions = computed(() => employees.value.filter((item) => `${item.position},${item.role},${item.business_roles}`.includes('客服')))

const dialogTitles: Record<DetailType, string> = {
  contact: '项目联系人', location: '项目位置', maintainer: '项目养护员', contract: '合同', plant: '项目植物', salary: '项目工资',
}

function resetObject(target: Row, values: Row) {
  Object.keys(target).forEach((key) => delete target[key])
  Object.assign(target, values)
}

function normalizeDates(payload: Row, fields: string[]) {
  const values = { ...payload }
  fields.forEach((field) => { if (!values[field]) values[field] = null })
  return values
}

async function loadLookups() {
  const [customerRes, employeeRes, productRes] = await Promise.all([
    api.get('/customers'), api.get('/employees'), api.get('/products'),
  ])
  customers.value = customerRes.data.items
  employees.value = employeeRes.data.items
  products.value = productRes.data.items
}

async function loadProjects() {
  loading.value = true
  try {
    projects.value = (await api.get('/projects', { params: { keyword: keyword.value.trim(), business: currentBusiness.value } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '项目加载失败')
  } finally {
    loading.value = false
  }
}

function openProject(row?: Row) {
  projectEditingId.value = row?.id || null
  resetObject(projectForm, row ? {
    code: row.code, customer_id: row.customer_id, name: row.name, address: row.address,
    business_types: row.business_types ? String(row.business_types).split(',').filter(Boolean) : [],
    plant_source: row.plant_source || '新采购',
    supervisor_id: row.supervisor_id, customer_service_id: row.customer_service_id,
    start_date: row.start_date, status: row.status, notes: row.notes,
  } : {
    code: `XM-${Date.now().toString().slice(-8)}`, customer_id: null, name: '', address: '', business_types: [currentBusiness.value], plant_source: '新采购',
    supervisor_id: null, customer_service_id: null, start_date: '', status: '进行中', notes: '',
  })
  projectDialog.value = true
}

function handleProjectCustomerChange() {
  const customer = customers.value.find((item) => item.id === projectForm.customer_id)
  if (!customer) return
  if (!projectForm.name && customer.project_name) projectForm.name = customer.project_name
  if (!projectForm.address && customer.address) projectForm.address = customer.address
  if (!projectForm.notes && (customer.contact_person || customer.phone)) {
    projectForm.notes = `负责人：${customer.contact_person || '-'}，电话：${customer.phone || '-'}`
  }
  const supervisor = employees.value.find((item) => item.name === customer.supervisor_name)
  if (!projectForm.supervisor_id && supervisor) projectForm.supervisor_id = supervisor.id
}

async function saveProject() {
  if (!projectForm.code || !projectForm.name || !projectForm.customer_id) return ElMessage.warning('请填写项目编码、名称并选择客户')
  saving.value = true
  try {
    const payload = normalizeDates({ ...projectForm, business_types: (projectForm.business_types || []).join(',') }, ['start_date'])
    if (projectEditingId.value) await api.put(`/projects/${projectEditingId.value}`, payload)
    else await api.post('/projects', payload)
    ElMessage.success(`项目${projectEditingId.value ? '修改' : '新增'}成功`)
    projectDialog.value = false
    await loadProjects()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '项目保存失败')
  } finally {
    saving.value = false
  }
}

async function loadDetail() {
  if (!selectedProject.value) return
  const id = selectedProject.value.id
  const responses = await Promise.all([
    api.get(`/projects/${id}/contacts`), api.get(`/projects/${id}/locations`), api.get(`/projects/${id}/maintainers`),
    api.get('/contracts', { params: { project_id: id } }), api.get('/project-plants', { params: { project_id: id } }),
    api.get('/project-salaries', { params: { project_id: id } }),
  ])
  ;[detail.contacts, detail.locations, detail.maintainers, detail.contracts, detail.plants, detail.salaries] = responses.map((item) => item.data.items)
}

async function showDetail(row: Row) {
  selectedProject.value = row
  activeTab.value = 'locations'
  detailVisible.value = true
  try { await loadDetail() } catch { ElMessage.error('项目详情加载失败') }
}

async function openPlantChanges(row: Row) {
  selectedPlant.value = row
  plantChangeDialog.value = true
  try {
    plantChanges.value = (await api.get('/project-plant-changes', { params: { plant_id: row.id } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '植物流水加载失败')
  }
}

function openSub(type: DetailType, row?: Row) {
  subType.value = type
  subEditingId.value = row?.id || null
  const defaults: Record<DetailType, Row> = {
    contact: { name: '', phone: '', position: '', contact_type: '项目负责人', priority: 1, notes: '' },
    location: { name: '', location_type: detail.locations.some((item) => item.location_type === '楼层') ? '区域' : '楼层', parent_id: null, sort_order: detail.locations.length + 1 },
    maintainer: { employee_id: null, area_description: '全部区域', is_primary: false, start_date: '', end_date: null, status: '负责中' },
    contract: { contract_no: `HT-${Date.now().toString().slice(-8)}`, name: '', contract_type: '整体合同', business_types: [currentBusiness.value], effective_date: '', end_date: '', billing_start_date: '', billing_cycle: '月付', amount: 0, reminder_days: 30, status: '生效', notes: '' },
    plant: { location_id: null, product_id: null, specification: '', quantity: 1, unit: '盆', decorative_pot: '', maintainer_id: null, entry_date: '', billing_start_date: '', status: '在场', notes: '' },
    salary: { employee_id: null, salary_month: new Date().toISOString().slice(0, 7), amount: 0, adjustment_reason: '', status: '未结算' },
  }
  const value = row ? { ...row } : defaults[type]
  if (type === 'contract') value.business_types = row?.business_types ? String(row.business_types).split(',').filter(Boolean) : defaults.contract.business_types
  resetObject(subForm, value)
  subDialog.value = true
}

function handlePlantProductChange() {
  if (subType.value !== 'plant') return
  const product = products.value.find((item) => item.id === subForm.product_id)
  if (!product) return
  subForm.specification = product.specification || subForm.specification || ''
  subForm.unit = product.project_unit || product.unit || subForm.unit || '盆'
}

async function saveSub() {
  if (!selectedProject.value) return
  saving.value = true
  const projectId = selectedProject.value.id
  try {
    if (subType.value === 'contact') await api.post(`/projects/${projectId}/contacts`, subForm)
    if (subType.value === 'location') await api.post(`/projects/${projectId}/locations`, subForm)
    if (subType.value === 'maintainer') await api.post(`/projects/${projectId}/maintainers`, normalizeDates(subForm, ['start_date', 'end_date']))
    if (subType.value === 'contract') {
      const payload = normalizeDates({ ...subForm, project_id: projectId, business_types: (subForm.business_types || []).join(',') }, ['effective_date', 'end_date', 'billing_start_date'])
      if (subEditingId.value) await api.put(`/contracts/${subEditingId.value}`, payload)
      else await api.post('/contracts', payload)
    }
    if (subType.value === 'plant') {
      const payload = normalizeDates({ ...subForm, project_id: projectId }, ['entry_date', 'billing_start_date'])
      if (subEditingId.value) await api.put(`/project-plants/${subEditingId.value}`, payload)
      else await api.post('/project-plants', payload)
    }
    if (subType.value === 'salary') {
      if (subEditingId.value) await api.put(`/project-salaries/${subEditingId.value}`, subForm)
      else await api.post('/project-salaries', { ...subForm, project_id: projectId })
    }
    ElMessage.success(`${dialogTitles[subType.value]}保存成功`)
    subDialog.value = false
    await loadDetail()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '保存失败，请检查填写内容')
  } finally {
    saving.value = false
  }
}

async function removeSub(type: 'contact' | 'location' | 'maintainer', row: Row) {
  await ElMessageBox.confirm(`确定移除“${row.name || row.employee_name}”吗？`, '操作确认', { type: 'warning' })
  const endpoints = { contact: '/project-contacts', location: '/project-locations', maintainer: '/project-maintainers' }
  try {
    await api.delete(`${endpoints[type]}/${row.id}`)
    ElMessage.success('操作成功')
    await loadDetail()
  } catch (error: any) { ElMessage.error(error.response?.data?.detail || '操作失败') }
}

function locationPath(location: Row) {
  const names = [location.name]
  let parentId = location.parent_id
  while (parentId) {
    const parent = detail.locations.find((item) => item.id === parentId)
    if (!parent) break
    names.unshift(parent.name)
    parentId = parent.parent_id
  }
  return names.join(' / ')
}

function money(value: unknown) { return `¥${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}` }

function moneyText(value: unknown) {
  return `¥${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function plantImage(row: Row) {
  return row.variant_image_url || row.product_image_url || ''
}

function plantAmount(row: Row) {
  return Number(row.quantity || 0) * Number(row.unit_price || 0)
}

function plantLocation(row: Row) {
  const location = detail.locations.find((item) => item.id === row.location_id)
  return location ? locationPath(location) : row.location_name || '-'
}

function projectDocumentRows() {
  const project = selectedProject.value || {}
  const contact = detail.contacts[0] || {}
  const maintainer = detail.maintainers.find((item) => item.is_primary) || detail.maintainers[0] || {}
  const contract = detail.contracts[0] || {}
  const totalAmount = Number(contract.amount || 0)
  return [
    [
      { label: '项目名称', value: project.name || '-' },
      { label: '客户名称', value: project.customer_name || '-' },
      { label: '项目负责人', value: project.supervisor_name || '-' },
    ],
    [
      { label: '联系人', value: contact.name || maintainer.employee_name || '-' },
      { label: '联系电话', value: contact.phone || maintainer.employee_phone || '-' },
      { label: '地址', value: project.address || '-' },
    ],
    [
      { label: '项目类型', value: project.business_types || '-' },
      { label: '项目进度', value: project.status || '-' },
      { label: '项目金额', value: totalAmount ? moneyText(totalAmount) : '-' },
    ],
    [
      { label: '租赁开始时间', value: contract.billing_start_date || contract.effective_date || project.start_date || '-' },
      { label: '租赁时长', value: contract.effective_date && contract.end_date ? `${contract.effective_date} 至 ${contract.end_date}` : '-' },
      { label: '付款方式', value: contract.billing_cycle || '-' },
    ],
    [
      { label: '月租金', value: totalAmount ? moneyText(totalAmount) : '-' },
      { label: '植物来源', value: project.plant_source || '-' },
      { label: '项目备注', value: project.notes || '-' },
    ],
  ]
}

onMounted(async () => {
  try { await Promise.all([loadLookups(), loadProjects()]) } catch { ElMessage.error('基础资料加载失败') }
})

watch(() => route.query.business, () => {
  keyword.value = ''
  loadProjects()
})
</script>

<template>
  <div class="page project-page">
    <div class="page-heading compact">
      <div><p class="eyebrow">PROJECT FOUNDATION</p><h1>{{ pageTitle }}</h1><p>以项目为中心管理位置、联系人、养护员、合同、植物台账和项目工资。</p></div>
      <el-button type="success" :icon="Plus" @click="openProject()">新增项目</el-button>
    </div>
    <article class="panel table-panel">
      <div class="crud-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="搜索项目编码、名称或地址" @keyup.enter="loadProjects" @clear="loadProjects" />
        <el-button type="success" plain :icon="Search" @click="loadProjects">查询</el-button>
        <el-button :icon="Refresh" @click="keyword = ''; loadProjects()">重置</el-button>
        <span class="crud-count">共 {{ projects.length }} 个项目</span>
      </div>
      <el-table v-loading="loading" :data="projects" stripe empty-text="暂无项目">
        <el-table-column prop="code" label="项目编码" width="125" />
        <el-table-column prop="name" label="项目名称" min-width="170" />
        <el-table-column prop="customer_name" label="客户" min-width="160" />
        <el-table-column prop="business_types" label="业务类型" min-width="160" />
        <el-table-column prop="supervisor_name" label="主管" width="100" />
        <el-table-column prop="customer_service_name" label="客服" width="100" />
        <el-table-column prop="address" label="项目地址" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="90"><template #default="scope"><el-tag :type="scope.row.status === '进行中' ? 'success' : 'info'">{{ scope.row.status }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="95">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">更多<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="showDetail(scope.row)">详情</el-dropdown-item>
                  <el-dropdown-item @click="openProject(scope.row)">编辑</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <el-dialog v-model="projectDialog" :title="`${projectEditingId ? '编辑' : '新增'}项目`" width="760px">
      <el-form label-position="top" class="foundation-form">
        <el-form-item label="项目编码" required><el-input v-model="projectForm.code" /></el-form-item>
        <el-form-item label="项目名称" required><el-input v-model="projectForm.name" /></el-form-item>
        <el-form-item label="所属客户" required><el-select v-model="projectForm.customer_id" filterable style="width:100%" @change="handleProjectCustomerChange"><el-option v-for="item in customers" :key="item.id" :label="`${item.name}${item.project_name ? ' · ' + item.project_name : ''}`" :value="item.id" /></el-select></el-form-item>
        <el-form-item label="业务类型"><el-select v-model="projectForm.business_types" multiple style="width:100%"><el-option v-for="item in businessOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item>
        <el-form-item label="进场植物来源"><el-select v-model="projectForm.plant_source" style="width:100%"><el-option v-for="item in ['新采购','仓库库存','买断上一家','混合来源','其他']" :key="item" :label="item" :value="item" /></el-select></el-form-item>
        <el-form-item label="负责主管"><el-select v-model="projectForm.supervisor_id" clearable filterable style="width:100%"><el-option v-for="item in supervisorOptions" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
        <el-form-item label="负责客服"><el-select v-model="projectForm.customer_service_id" clearable filterable style="width:100%"><el-option v-for="item in customerServiceOptions" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
        <el-form-item label="开始日期"><el-date-picker v-model="projectForm.start_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="状态"><el-select v-model="projectForm.status" style="width:100%"><el-option v-for="item in ['筹备中','进行中','已暂停','已结束']" :key="item" :label="item" :value="item" /></el-select></el-form-item>
        <el-form-item label="项目地址" class="wide"><el-input v-model="projectForm.address" /></el-form-item>
        <el-form-item label="备注" class="wide"><el-input v-model="projectForm.notes" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="projectDialog = false">取消</el-button><el-button type="success" :loading="saving" @click="saveProject">保存</el-button></template>
    </el-dialog>

    <el-drawer v-model="detailVisible" :title="selectedProject ? `${selectedProject.name} · 项目档案` : '项目档案'" size="88%" destroy-on-close>
      <div v-if="selectedProject" class="project-summary">
        <div><span>所属客户</span><strong>{{ selectedProject.customer_name }}</strong></div><div><span>业务类型</span><strong>{{ selectedProject.business_types }}</strong></div><div><span>植物来源</span><strong>{{ selectedProject.plant_source }}</strong></div><div><span>项目主管</span><strong>{{ selectedProject.supervisor_name || '未设置' }}</strong></div><div><span>项目状态</span><strong>{{ selectedProject.status }}</strong></div>
      </div>
      <el-tabs v-model="activeTab" class="project-tabs">
        <el-tab-pane label="位置层级" name="locations">
          <div class="detail-toolbar"><p>项目位置固定按“楼层 / 区域”建立。</p><el-button type="success" :icon="Plus" @click="openSub('location')">新增位置</el-button></div>
          <el-table :data="detail.locations"><el-table-column label="完整位置" min-width="300"><template #default="scope">{{ locationPath(scope.row) }}</template></el-table-column><el-table-column prop="location_type" label="类型" width="120" /><el-table-column label="操作" width="95"><template #default="scope"><el-dropdown trigger="click"><el-button link type="primary" class="table-more-button">更多<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item @click="removeSub('location', scope.row)">删除</el-dropdown-item></el-dropdown-menu></template></el-dropdown></template></el-table-column></el-table>
        </el-tab-pane>
        <el-tab-pane label="联系人" name="contacts">
          <div class="detail-toolbar"><p>联系人按数字优先级从小到大排序。</p><el-button type="success" :icon="Plus" @click="openSub('contact')">新增联系人</el-button></div>
          <el-table :data="detail.contacts"><el-table-column prop="priority" label="优先级" width="90" /><el-table-column prop="name" label="姓名" /><el-table-column prop="contact_type" label="类型" /><el-table-column prop="position" label="职务" /><el-table-column prop="phone" label="电话" /><el-table-column label="操作" width="95"><template #default="scope"><el-dropdown trigger="click"><el-button link type="primary" class="table-more-button">更多<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item @click="removeSub('contact', scope.row)">删除</el-dropdown-item></el-dropdown-menu></template></el-dropdown></template></el-table-column></el-table>
        </el-tab-pane>
        <el-tab-pane label="养护员" name="maintainers">
          <div class="detail-toolbar"><p>支持一个项目多位养护员，并划分负责区域。</p><el-button type="success" :icon="Plus" @click="openSub('maintainer')">分配养护员</el-button></div>
          <el-table :data="detail.maintainers"><el-table-column prop="employee_name" label="养护员" /><el-table-column prop="employee_phone" label="电话" /><el-table-column prop="area_description" label="负责区域" min-width="200" /><el-table-column label="主要联系人" width="110"><template #default="scope">{{ scope.row.is_primary ? '是' : '否' }}</template></el-table-column><el-table-column prop="status" label="状态" /><el-table-column label="操作" width="95"><template #default="scope"><el-dropdown trigger="click"><el-button link type="primary" class="table-more-button">更多<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item @click="removeSub('maintainer', scope.row)">结束负责</el-dropdown-item></el-dropdown-menu></template></el-dropdown></template></el-table-column></el-table>
        </el-tab-pane>
        <el-tab-pane label="合同" name="contracts">
          <div class="detail-toolbar"><p>支持整体合同、分体合同及不同计费周期。</p><el-button type="success" :icon="Plus" @click="openSub('contract')">新增合同</el-button></div>
          <el-table :data="detail.contracts"><el-table-column prop="contract_no" label="合同编号" width="140" /><el-table-column prop="name" label="合同名称" min-width="180" /><el-table-column prop="contract_type" label="类型" /><el-table-column prop="business_types" label="业务" /><el-table-column prop="effective_date" label="生效日" width="110" /><el-table-column prop="end_date" label="结束日" width="110" /><el-table-column label="金额" width="130"><template #default="scope">{{ money(scope.row.amount) }}</template></el-table-column><el-table-column prop="status" label="状态" /><el-table-column label="操作" width="95"><template #default="scope"><el-dropdown trigger="click"><el-button link type="primary" class="table-more-button">更多<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item @click="openSub('contract', scope.row)">编辑</el-dropdown-item></el-dropdown-menu></template></el-dropdown></template></el-table-column></el-table>
        </el-tab-pane>
        <el-tab-pane label="项目植物" name="plants">
          <div class="detail-toolbar"><p>同一位置、商品和规格可合并记录数量；流水记录每次进场、换花、撤花和换盆。</p><el-button type="success" :icon="Plus" @click="openSub('plant')">新增植物</el-button></div>
          <div class="document-detail project-plant-document">
            <section class="document-card">
              <div class="document-title">
                <strong>详细信息</strong>
                <span>{{ selectedProject?.name }} · 项目植物列表</span>
              </div>
              <table class="document-info-table">
                <tbody>
                  <tr v-for="(row, rowIndex) in projectDocumentRows()" :key="rowIndex">
                    <td v-for="cell in row" :key="cell.label">
                      <span>{{ cell.label }}：</span>
                      <strong>{{ cell.value }}</strong>
                    </td>
                  </tr>
                </tbody>
              </table>
            </section>

            <section class="document-card">
              <div class="document-title">
                <strong>植物详情</strong>
                <span>按楼层 / 区域记录实际摆放植物</span>
              </div>
              <el-table :data="detail.plants" border class="document-plant-table">
                <el-table-column prop="product_name" label="名称" min-width="150" />
                <el-table-column label="产品图" width="115">
                  <template #default="scope">
                    <el-image v-if="plantImage(scope.row)" class="document-product-image" :src="plantImage(scope.row)" fit="cover" />
                    <div v-else class="document-product-empty">无图</div>
                  </template>
                </el-table-column>
                <el-table-column label="规格" min-width="120">
                  <template #default="scope">{{ scope.row.specification || '-' }}</template>
                </el-table-column>
                <el-table-column prop="unit" label="单位" width="80" />
                <el-table-column label="数量" width="90"><template #default="scope">{{ scope.row.quantity }}</template></el-table-column>
                <el-table-column label="单价/盆" width="105"><template #default="scope">{{ moneyText(scope.row.unit_price) }}</template></el-table-column>
                <el-table-column label="金额/月" width="115"><template #default="scope">{{ moneyText(plantAmount(scope.row)) }}</template></el-table-column>
                <el-table-column label="摆放位置" min-width="165"><template #default="scope">{{ plantLocation(scope.row) }}</template></el-table-column>
                <el-table-column prop="decorative_pot" label="装饰花盆" min-width="120" />
                <el-table-column prop="maintainer_name" label="养护员" width="95" />
                <el-table-column prop="status" label="状态" width="90" />
                <el-table-column label="操作" width="95">
                  <template #default="scope">
                    <el-dropdown trigger="click">
                      <el-button link type="primary" class="table-more-button">更多<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item @click="openSub('plant', scope.row)">编辑</el-dropdown-item>
                          <el-dropdown-item @click="openPlantChanges(scope.row)">流水</el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                  </template>
                </el-table-column>
              </el-table>
            </section>
          </div>
        </el-tab-pane>
        <el-tab-pane label="项目工资" name="salaries">
          <div class="detail-toolbar"><p>由主管按月填写每位养护员在本项目的工资。</p><el-button type="success" :icon="Plus" @click="openSub('salary')">录入工资</el-button></div>
          <el-table :data="detail.salaries"><el-table-column prop="salary_month" label="月份" /><el-table-column prop="employee_name" label="养护员" /><el-table-column label="项目工资"><template #default="scope">{{ money(scope.row.amount) }}</template></el-table-column><el-table-column prop="adjustment_reason" label="调整原因" min-width="220" /><el-table-column prop="status" label="状态" /><el-table-column label="操作" width="95"><template #default="scope"><el-dropdown trigger="click"><el-button link type="primary" class="table-more-button">更多<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item @click="openSub('salary', scope.row)">编辑</el-dropdown-item></el-dropdown-menu></template></el-dropdown></template></el-table-column></el-table>
        </el-tab-pane>
      </el-tabs>
    </el-drawer>

    <el-dialog v-model="subDialog" :title="`${subEditingId ? '编辑' : '新增'}${dialogTitles[subType]}`" width="700px">
      <el-form label-position="top" class="foundation-form">
        <template v-if="subType === 'contact'">
          <el-form-item label="姓名" required><el-input v-model="subForm.name" /></el-form-item><el-form-item label="电话"><el-input v-model="subForm.phone" /></el-form-item><el-form-item label="职务"><el-input v-model="subForm.position" /></el-form-item><el-form-item label="联系人类型"><el-select v-model="subForm.contact_type" style="width:100%"><el-option v-for="item in ['项目负责人','甲方联系人','财务联系人','其他']" :key="item" :label="item" :value="item" /></el-select></el-form-item><el-form-item label="联系优先级"><el-input-number v-model="subForm.priority" :min="1" style="width:100%" /></el-form-item><el-form-item label="备注"><el-input v-model="subForm.notes" /></el-form-item>
        </template>
        <template v-if="subType === 'location'">
          <el-form-item label="位置名称" required><el-input v-model="subForm.name" :placeholder="subForm.location_type === '楼层' ? '例如：1楼' : '例如：总经理办公室'" /></el-form-item><el-form-item label="位置类型"><el-select v-model="subForm.location_type" style="width:100%" @change="subForm.parent_id = null"><el-option label="楼层" value="楼层" /><el-option label="区域" value="区域" /></el-select></el-form-item><el-form-item v-if="subForm.location_type === '区域'" label="所属楼层" required><el-select v-model="subForm.parent_id" style="width:100%"><el-option v-for="item in detail.locations.filter((location) => location.location_type === '楼层')" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item label="排序"><el-input-number v-model="subForm.sort_order" :min="0" style="width:100%" /></el-form-item>
        </template>
        <template v-if="subType === 'maintainer'">
          <el-form-item label="养护员" required><el-select v-model="subForm.employee_id" filterable style="width:100%"><el-option v-for="item in maintainerOptions" :key="item.id" :label="`${item.name} · ${item.phone || '无电话'}`" :value="item.id" /></el-select></el-form-item><el-form-item label="负责区域"><el-input v-model="subForm.area_description" /></el-form-item><el-form-item label="开始日期"><el-date-picker v-model="subForm.start_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item><el-form-item label="主要联系人"><el-switch v-model="subForm.is_primary" active-text="是" inactive-text="否" /></el-form-item>
        </template>
        <template v-if="subType === 'contract'">
          <el-form-item label="合同编号" required><el-input v-model="subForm.contract_no" /></el-form-item><el-form-item label="合同名称" required><el-input v-model="subForm.name" /></el-form-item><el-form-item label="合同类型"><el-select v-model="subForm.contract_type" style="width:100%"><el-option label="整体合同" value="整体合同" /><el-option label="分体合同" value="分体合同" /></el-select></el-form-item><el-form-item label="覆盖业务"><el-select v-model="subForm.business_types" multiple style="width:100%"><el-option v-for="item in businessOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item><el-form-item label="生效日期" required><el-date-picker v-model="subForm.effective_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item><el-form-item label="结束日期" required><el-date-picker v-model="subForm.end_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item><el-form-item label="计费开始日期"><el-date-picker v-model="subForm.billing_start_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item><el-form-item label="付款周期"><el-select v-model="subForm.billing_cycle" style="width:100%"><el-option v-for="item in ['月付','季付','半年付','年付','一次性','自定义']" :key="item" :label="item" :value="item" /></el-select></el-form-item><el-form-item label="合同金额"><el-input-number v-model="subForm.amount" :min="0" :precision="2" style="width:100%" /></el-form-item><el-form-item label="提前提醒天数"><el-input-number v-model="subForm.reminder_days" :min="0" style="width:100%" /></el-form-item><el-form-item label="状态"><el-select v-model="subForm.status" style="width:100%"><el-option v-for="item in ['草稿','生效','暂停','到期','终止']" :key="item" :label="item" :value="item" /></el-select></el-form-item><el-form-item label="备注"><el-input v-model="subForm.notes" /></el-form-item>
        </template>
        <template v-if="subType === 'plant'">
          <el-form-item label="项目位置" required><el-select v-model="subForm.location_id" filterable style="width:100%"><el-option v-for="item in detail.locations" :key="item.id" :label="locationPath(item)" :value="item.id" /></el-select></el-form-item><el-form-item label="植物商品" required><el-select v-model="subForm.product_id" filterable style="width:100%" @change="handlePlantProductChange"><el-option v-for="item in products" :key="item.id" :label="`${item.name} · ${item.specification || '未设规格'}`" :value="item.id" /></el-select></el-form-item><el-form-item label="实际规格"><el-input v-model="subForm.specification" /></el-form-item><el-form-item label="数量"><el-input-number v-model="subForm.quantity" :min="0.01" :precision="2" style="width:100%" /></el-form-item><el-form-item label="单位"><el-input v-model="subForm.unit" /></el-form-item><el-form-item label="装饰花盆"><el-input v-model="subForm.decorative_pot" placeholder="可不填，项目列表默认折叠" /></el-form-item><el-form-item label="植物来源"><el-input :model-value="selectedProject?.plant_source" disabled /><small class="form-hint">来源在项目进场前设置，新增清单自动继承。</small></el-form-item><el-form-item label="养护员"><el-select v-model="subForm.maintainer_id" clearable style="width:100%"><el-option v-for="item in maintainerOptions" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item label="入场日期"><el-date-picker v-model="subForm.entry_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item><el-form-item label="计费开始日"><el-date-picker v-model="subForm.billing_start_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item><el-form-item label="状态"><el-select v-model="subForm.status" style="width:100%"><el-option v-for="item in ['在场','待更换','已撤场','已丢失']" :key="item" :label="item" :value="item" /></el-select></el-form-item><el-form-item label="备注"><el-input v-model="subForm.notes" /></el-form-item>
        </template>
        <template v-if="subType === 'salary'">
          <el-form-item v-if="!subEditingId" label="养护员" required><el-select v-model="subForm.employee_id" style="width:100%"><el-option v-for="item in maintainerOptions" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item v-if="!subEditingId" label="工资月份" required><el-date-picker v-model="subForm.salary_month" type="month" value-format="YYYY-MM" style="width:100%" /></el-form-item><el-form-item label="本项目工资"><el-input-number v-model="subForm.amount" :min="0" :precision="2" style="width:100%" /></el-form-item><el-form-item label="调整原因"><el-input v-model="subForm.adjustment_reason" /></el-form-item><el-form-item label="状态"><el-select v-model="subForm.status" style="width:100%"><el-option label="未结算" value="未结算" /><el-option label="已结算" value="已结算" /></el-select></el-form-item>
        </template>
      </el-form>
      <template #footer><el-button @click="subDialog = false">取消</el-button><el-button type="success" :loading="saving" @click="saveSub">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="plantChangeDialog" :title="selectedPlant ? `${selectedPlant.product_name} · 变动流水` : '植物变动流水'" width="980px" top="6vh" destroy-on-close>
      <div v-if="selectedPlant" class="plant-change-head">
        <div><span>位置</span><strong>{{ selectedPlant.location_name || '-' }}</strong></div>
        <div><span>规格</span><strong>{{ selectedPlant.specification || '-' }}</strong></div>
        <div><span>当前数量</span><strong>{{ selectedPlant.quantity }} {{ selectedPlant.unit }}</strong></div>
        <div><span>装饰花盆</span><strong>{{ selectedPlant.decorative_pot || '-' }}</strong></div>
      </div>
      <el-table :data="plantChanges" stripe border empty-text="暂无变动流水">
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="scope">{{ String(scope.row.created_at || '').replace('T', ' ').slice(0, 16) }}</template>
        </el-table-column>
        <el-table-column prop="change_type" label="类型" width="95" />
        <el-table-column prop="source_no" label="来源单号" min-width="135">
          <template #default="scope">{{ scope.row.source_no || '-' }}</template>
        </el-table-column>
        <el-table-column label="数量变化" width="170">
          <template #default="scope">
            {{ scope.row.quantity_before }} → {{ scope.row.quantity_after }}
            <el-tag size="small" :type="Number(scope.row.quantity_delta) >= 0 ? 'success' : 'danger'" effect="plain">
              {{ Number(scope.row.quantity_delta) >= 0 ? '+' : '' }}{{ scope.row.quantity_delta }}{{ scope.row.unit }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="花盆变化" min-width="180">
          <template #default="scope">{{ scope.row.pot_before || '-' }} → {{ scope.row.pot_after || '-' }}</template>
        </el-table-column>
        <el-table-column prop="operator" label="操作人" width="95">
          <template #default="scope">{{ scope.row.operator || '-' }}</template>
        </el-table-column>
        <el-table-column prop="notes" label="说明" min-width="220" show-overflow-tooltip />
      </el-table>
      <template #footer><el-button type="success" @click="plantChangeDialog = false">关闭</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.plant-change-head {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.plant-change-head div {
  border: 1px solid #dbeafe;
  border-radius: 14px;
  background: linear-gradient(135deg, #f8fbff 0%, #eef7ff 100%);
  padding: 12px 14px;
}

.plant-change-head span {
  display: block;
  color: #7b8794;
  font-size: 12px;
  margin-bottom: 6px;
}

.plant-change-head strong {
  color: #1f2937;
  font-size: 14px;
}
</style>

