<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, Plus, Refresh, Search, View } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const orders = ref<Row[]>([])
const products = ref<Row[]>([])
const productOptions = ref<Row[]>([])
const projects = ref<Row[]>([])
const customers = ref<Row[]>([])
const employees = ref<Row[]>([])
const vehicles = ref<Row[]>([])
const variantCache = reactive<Record<number, Row[]>>({})
const dialogVisible = ref(false)
const detailVisible = ref(false)
const progressVisible = ref(false)
const scheduleVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<Row>({})
const scheduleForm = reactive<Row>({})
const detailOrder = ref<Row | null>(null)
const progressOrder = ref<Row | null>(null)
const columnSettingVisible = ref(false)
const selectedOrders = ref<Row[]>([])

const typeMeta: Record<string, { title: string; apiType: string; prefix: string; desc: string }> = {
  lease: { title: '租赁订单', apiType: 'lease', prefix: 'ZB', desc: '用于租摆进场、项目增减植物和租摆业务派工前的订单登记。' },
  sales: { title: '销售订单', apiType: 'sales', prefix: 'XS', desc: '用于临时销售、客户自提、货拉拉直送或公司配送的销售登记。' },
  exchange: { title: '换花订单', apiType: 'exchange', prefix: 'HH', desc: '用于养护员报换、主管换品种和客服接单后的换花流程。' },
  gift: { title: '赠送单', apiType: 'gift', prefix: 'ZS', desc: '用于客户赠送、活动赠品或售后赠送，流程可按需生成采购和配送安排。' },
  withdraw: { title: '撤花单', apiType: 'withdraw', prefix: 'CH', desc: '用于主管或客服安排撤出某项目、楼层、区域或单盆植物，完成后会扣减项目植物清单。' },
  maintenance: { title: '养护订单', apiType: 'maintenance', prefix: 'YH', desc: '用于修剪、打药、室外养护和临时养护工程任务登记。' },
  delivery: { title: '配送订单', apiType: 'delivery', prefix: 'PS', desc: '用于记录配送类任务和相关人员可见的处理进度。' },
  engineering: { title: '工程订单', apiType: 'engineering', prefix: 'GC', desc: '用于工程绿化项目的草皮、灌木、乔木养护、修剪、补种和施工协助登记。' },
  'engineering-service': { title: '修剪/补种任务', apiType: 'engineering-service', prefix: 'GJ', desc: '用于工程项目免费或收费修剪、补种、派人协助等任务登记。' },
  'engineering-material': { title: '工程物料任务', apiType: 'engineering-material', prefix: 'GW', desc: '用于工程项目需要采购再配送的物料需求。' },
  'grid-greenwind': { title: '电网绿风订单', apiType: 'grid-greenwind', prefix: 'DL', desc: '用于电网业务中绿风公司供货订单，商品默认取绿风电网合同价。' },
  'grid-shengjing': { title: '电网盛景订单', apiType: 'grid-shengjing', prefix: 'DS', desc: '用于电网业务中盛景公司供货订单，商品默认取盛景电网合同价。' },
  cleaning: { title: '保洁订单', apiType: 'cleaning', prefix: 'BJ', desc: '用于保洁项目订单、物料配送和现场协助任务登记。' },
  'cleaning-service': { title: '保洁任务', apiType: 'cleaning-service', prefix: 'BR', desc: '用于保洁项目修剪、协助、临时派工等任务登记。' },
  'cleaning-material': { title: '保洁物料配送', apiType: 'cleaning-material', prefix: 'BW', desc: '用于保洁项目需要采购再配送的物料需求。' },
}

const currentKey = computed(() => String(route.params.orderType || 'lease'))
const meta = computed(() => typeMeta[currentKey.value] || typeMeta.lease)
const projectBusiness = computed(() => {
  if (meta.value.apiType.startsWith('engineering')) return '工程绿化'
  if (meta.value.apiType.startsWith('grid')) return '电网'
  if (meta.value.apiType.startsWith('cleaning')) return '保洁'
  return '租摆'
})
const orderColumns = [
  { key: 'order_no', label: '订单号' },
  { key: 'project_name', label: '项目' },
  { key: 'customer_name', label: '客户' },
  { key: 'requester', label: '报单/接单人' },
  { key: 'order_date', label: '下单日期' },
  { key: 'expected_date', label: '期望完成' },
  { key: 'items', label: '明细' },
  { key: 'amount', label: '金额' },
  { key: 'priority', label: '优先级' },
  { key: 'flow', label: '流程' },
  { key: 'current_step', label: '当前步骤' },
  { key: 'progress', label: '流程进度' },
  { key: 'status', label: '状态' },
]
const defaultColumnKeys = orderColumns.map((item) => item.key)
const visibleColumnKeys = ref<string[]>([...defaultColumnKeys])
const columnStorageKey = computed(() => {
  const saved = localStorage.getItem('greenwind_user')
  const user = saved ? JSON.parse(saved) : {}
  return `greenwind_order_columns_${user?.username || user?.id || 'guest'}_${meta.value.apiType}`
})
function loadColumnSetting() {
  const saved = localStorage.getItem(columnStorageKey.value)
  visibleColumnKeys.value = saved ? parseJson<string[]>(saved, defaultColumnKeys).filter((key) => defaultColumnKeys.includes(key)) : [...defaultColumnKeys]
  ;['current_step', 'status'].forEach((key) => {
    if (!visibleColumnKeys.value.includes(key)) visibleColumnKeys.value.push(key)
  })
  if (!visibleColumnKeys.value.length) visibleColumnKeys.value = [...defaultColumnKeys]
}
function saveColumnSetting() {
  localStorage.setItem(columnStorageKey.value, JSON.stringify(visibleColumnKeys.value))
  ElMessage.success('表头显示已保存')
  columnSettingVisible.value = false
}
function showColumn(key: string) { return visibleColumnKeys.value.includes(key) }

function handleSelectionChange(rows: Row[]) {
  selectedOrders.value = rows
}

function nextOrderNo() {
  const prefix = meta.value.prefix
  const maxNo = orders.value
    .map((row) => String(row.order_no || '').match(new RegExp(`^${prefix}(\\d{6})$`))?.[1])
    .filter(Boolean)
    .map((value) => Number(value))
    .reduce((max, value) => Math.max(max, value), 0)
  return `${prefix}${String(maxNo + 1).padStart(6, '0')}`
}

function resetForm(values: Row) {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, values)
}

function resetScheduleForm(values: Row) {
  Object.keys(scheduleForm).forEach((key) => delete scheduleForm[key])
  Object.assign(scheduleForm, values)
}

function emptyItem() {
  return { product_key: '', product_id: null, variant_id: null, product_name: '', variant_name: '', location_text: '', quantity: 1, unit: '件', unit_price: 0, notes: '' }
}

function emptyOrder() {
  return {
    order_no: nextOrderNo(),
    order_type: meta.value.apiType,
    project_id: null,
    customer_id: null,
    project_name: '',
    customer_name: '',
    requester: '',
    contact_phone: '',
    order_date: new Date().toISOString().slice(0, 10),
    expected_date: '',
    priority: '普通',
    need_purchase: false,
    need_delivery: true,
    status: '待处理',
    notes: '',
    items: [emptyItem()],
  }
}

function parseJson<T>(value: string | undefined, fallback: T): T {
  if (!value) return fallback
  try { return JSON.parse(value) as T } catch { return fallback }
}

function variantLabel(item: Row) {
  const values = parseJson<Record<string, string>>(item.specification_values, {})
  return Object.values(values).filter(Boolean).join(' · ') || item.specification || item.code
}

function formatNumber(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') return ''
  const number = Number(value)
  if (Number.isNaN(number)) return ''
  return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
}

function orderUnitPrice(product: Row, variant?: Row) {
  if (meta.value.apiType === 'grid-greenwind') {
    return variant?.grid_greenwind_price || product.grid_greenwind_price || variant?.sale_price || product.sale_price || 0
  }
  if (meta.value.apiType === 'grid-shengjing') {
    return variant?.grid_shengjing_price || product.grid_shengjing_price || variant?.sale_price || product.sale_price || 0
  }
  if (meta.value.apiType === 'lease' || meta.value.apiType === 'exchange') {
    return variant?.monthly_rental_price || product.monthly_rental_price || variant?.sale_price || product.sale_price || 0
  }
  return variant?.sale_price || variant?.monthly_rental_price || product.sale_price || product.monthly_rental_price || 0
}

function orderTotal(row: Row) {
  return (row.items || []).reduce((sum: number, item: Row) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0)
}

function itemImage(item: Row) {
  if (item.variant_id) {
    const variant = (variantCache[item.product_id] || []).find((entry) => entry.id === item.variant_id)
    if (variant?.image_url) return variant.image_url
  }
  const product = products.value.find((entry) => entry.id === item.product_id)
  return item.variant_image_url || item.product_image_url || product?.image_url || ''
}

function itemAmount(item: Row) {
  return Number(item.amount || 0) || Number(item.quantity || 0) * Number(item.unit_price || 0)
}

function orderDocumentRows(row: Row) {
  const amount = Number(row.contract_amount || 0) || orderTotal(row)
  return [
    [
      { label: '项目名称', value: row.project_name || '-' },
      { label: '客户名称', value: row.customer_name || '-' },
      { label: '项目负责人', value: row.project_supervisor_name || row.requester || '-' },
    ],
    [
      { label: '联系人', value: row.customer_contact_person || row.requester || '-' },
      { label: '联系电话', value: row.customer_phone || row.contact_phone || '-' },
      { label: '地址', value: row.project_address || '-' },
    ],
    [
      { label: '项目类型', value: row.project_business_types || meta.value.title },
      { label: '项目进度', value: row.status || '-' },
      { label: '项目金额', value: moneyText(amount) },
    ],
    [
      { label: '租赁开始时间', value: row.contract_billing_start_date || row.contract_effective_date || row.order_date || '-' },
      { label: '租赁时长', value: row.contract_effective_date && row.contract_end_date ? `${row.contract_effective_date} 至 ${row.contract_end_date}` : '-' },
      { label: '付款方式', value: row.contract_billing_cycle || '-' },
    ],
    [
      { label: '月租金', value: moneyText(amount) },
      { label: '订单号', value: row.order_no || '-' },
      { label: '备注', value: row.notes || '-' },
    ],
  ]
}

function moneyText(value: unknown) {
  return `¥${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function itemSummary(row: Row) {
  return (row.items || []).map((item: Row) => `${item.product_name || '事项'}${item.variant_name ? ' · ' + item.variant_name : ''} × ${formatNumber(item.quantity)}${item.unit}`).join('，')
}

function hasNode(row: Row, key: string, doneStatus = '') {
  const node = (row.progress || []).find((item: Row) => item.key === key)
  if (!node) return false
  return doneStatus ? node.status === doneStatus : !['未生成', '未到达'].includes(node.status)
}

function displayOrderStatus(status: string) {
  const map: Record<string, string> = {
    已完成: '完成',
    待派配送: '待配送',
    待派单: '待配送',
    待出库: '待配送',
    待完成: '完成',
    已送达: '配送中',
  }
  return map[status] || status
}

function purchaseDisabled(row: Row) {
  return !row.need_purchase || ['已取消', '待审批', '已驳回', '已完成'].includes(row.status) || hasNode(row, 'purchase')
}

function outboundDisabled(row: Row) {
  return true
}

function scheduleDisabled(row: Row) {
  if (['已取消', '待审批', '已驳回', '已完成'].includes(row.status)) return true
  if (!row.need_delivery) return true
  if (hasNode(row, 'delivery')) return true
  return row.need_purchase && !hasNode(row, 'inbound', '已入库')
}

function statusTagType(status: string) {
  if (status === '已完成') return 'success'
  if (status === '已取消') return 'info'
  if (status === '待审批') return 'danger'
  if (status === '已驳回') return 'danger'
  if (status === '配送中' || status === '已送达') return 'primary'
  if (status === '待入库') return 'warning'
  return 'warning'
}

function progressTagType(node: Row) {
  if (node.state === 'done') return 'success'
  if (node.state === 'rejected') return 'danger'
  if (node.state === 'active') return 'primary'
  return 'info'
}

function nextOrderAction(row: Row) {
  if (['已完成', '已取消', '已驳回'].includes(row.status)) {
    return { label: '查看进度', type: 'info', handler: () => openProgress(row), disabled: !(row.progress || []).length }
  }
  if (row.status === '待审批') {
    return { label: '待审批', type: 'warning', handler: () => openProgress(row), disabled: false }
  }
  if (!purchaseDisabled(row)) {
    return { label: '采购', type: 'warning', handler: () => createPurchase(row), disabled: false }
  }
  if (row.status === '待入库') {
    return { label: '入库', type: 'warning', handler: () => enterPurchaseOrder(row), disabled: false }
  }
  if (['待采购', '采购中'].includes(row.status) || hasNode(row, 'purchase') && !hasNode(row, 'inbound', '已入库')) {
    return { label: '采购', type: 'warning', handler: () => enterPurchaseOrder(row), disabled: false }
  }
  if (['待配送', '待派配送', '待派单', '待出库'].includes(row.status)) {
    return { label: '配送', type: 'primary', handler: () => enterDeliveryOrder(row), disabled: false }
  }
  if (['配送中', '已送达'].includes(row.status)) {
    return { label: '完成', type: 'success', handler: () => changeStatus(row, '已完成'), disabled: false }
  }
  if (!scheduleDisabled(row)) {
    return { label: '配送', type: 'primary', handler: () => enterDeliveryOrder(row), disabled: false }
  }
  if (!['已完成', '已取消'].includes(row.status)) {
    return { label: '查看进度', type: 'primary', handler: () => openProgress(row), disabled: !(row.progress || []).length }
  }
  return null
}

function currentStepTagType(row: Row) {
  const value = String(row.current_step || row.status || '')
  if (value.includes('完成')) return 'success'
  if (value.includes('取消') || value.includes('驳回')) return 'danger'
  if (value.includes('配送') || value.includes('采购') || value.includes('入库') || value.includes('出库')) return 'primary'
  if (value.includes('审批')) return 'warning'
  return 'info'
}

function openDetail(row: Row) {
  detailOrder.value = row
  detailVisible.value = true
}

function openProgress(row: Row) {
  progressOrder.value = row
  progressVisible.value = true
}

async function loadBaseData() {
  const [productResponse, projectResponse, customerResponse] = await Promise.all([
    api.get('/products', { params: { project_category: projectBusiness.value } }),
    api.get('/projects', { params: { business: projectBusiness.value } }),
    api.get('/customers'),
  ])
  products.value = productResponse.data.items
  projects.value = projectResponse.data.items
  customers.value = customerResponse.data.items
  await Promise.all(products.value.map((product) => loadVariants(product.id)))
  productOptions.value = products.value.flatMap((product) => {
    const variants = variantCache[product.id] || []
    if (!variants.length) {
      return [{
        key: `${product.id}:`,
        product_id: product.id,
        variant_id: null,
        label: `${product.name}${product.specification ? ' · ' + product.specification : ''}`,
        product_name: product.name,
        variant_name: product.specification || '',
        unit: product.project_unit || product.unit || '件',
        unit_price: orderUnitPrice(product),
        image_url: product.image_url || '',
      }]
    }
    return variants.map((variant) => ({
      key: `${product.id}:${variant.id}`,
      product_id: product.id,
      variant_id: variant.id,
      label: `${product.name} · ${variantLabel(variant)}`,
      product_name: product.name,
      variant_name: variantLabel(variant),
      unit: variant.unit || product.project_unit || product.unit || '件',
      unit_price: orderUnitPrice(product, variant),
      image_url: variant.image_url || product.image_url || '',
    }))
  })
}

async function loadScheduleOptions() {
  const [employeeResponse, vehicleResponse] = await Promise.all([api.get('/employees'), api.get('/vehicles')])
  employees.value = employeeResponse.data.items
  vehicles.value = vehicleResponse.data.items
}

async function loadVariants(productId: number | string | null) {
  const key = Number(productId)
  if (!key || variantCache[key]) return
  variantCache[key] = (await api.get(`/products/${key}/variants`)).data.items
}

async function loadOrders() {
  loadColumnSetting()
  loading.value = true
  try {
    orders.value = (await api.get('/orders', { params: { order_type: meta.value.apiType, keyword: keyword.value.trim() } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '订单加载失败')
  } finally {
    loading.value = false
  }
}

async function openCreate() {
  editingId.value = null
  await loadBaseData()
  resetForm(emptyOrder())
  dialogVisible.value = true
}

async function openEdit(row: Row) {
  editingId.value = row.id
  await loadBaseData()
  await Promise.all((row.items || []).map((item: Row) => loadVariants(item.product_id)))
  resetForm({ ...row, order_type: meta.value.apiType, items: (row.items || []).map((item: Row) => ({ ...item, product_key: item.product_id ? `${item.product_id}:${item.variant_id || ''}` : '' })) })
  dialogVisible.value = true
}

function addItem() {
  form.items.push(emptyItem())
}

function removeItem(index: number | string) {
  if (form.items.length === 1) { ElMessage.warning('至少保留一条订单明细'); return }
  form.items.splice(Number(index), 1)
}

function fillCustomerInfo(customer: Row | undefined, overwriteProject = false) {
  if (!customer) return
  form.customer_id = customer.id
  form.customer_name = customer.name || form.customer_name
  form.requester = customer.maintainer_name || customer.contact_person || form.requester
  form.contact_phone = customer.maintainer_phone || customer.phone || form.contact_phone
  if (overwriteProject && customer.project_name) form.project_name = customer.project_name
}

function handleProjectChange() {
  const project = projects.value.find((entry) => entry.id === form.project_id)
  form.project_name = project?.name || form.project_name
  form.customer_name = project?.customer_name || form.customer_name
  if (project?.customer_id) {
    const customer = customers.value.find((entry) => entry.id === project.customer_id)
    fillCustomerInfo(customer)
  }
}

function handleCustomerChange() {
  const customer = customers.value.find((entry) => entry.id === form.customer_id)
  fillCustomerInfo(customer, !form.project_id)
}

async function handleProductChange(item: Row) {
  const option = productOptions.value.find((entry) => entry.key === item.product_key)
  if (!option) {
    item.product_id = null
    item.variant_id = null
    item.product_name = ''
    item.variant_name = ''
    item.unit = '件'
    item.unit_price = 0
    return
  }
  item.product_id = option.product_id
  item.variant_id = option.variant_id
  item.product_name = option.product_name
  item.variant_name = option.variant_name
  item.product_image_url = option.image_url
  item.variant_image_url = option.image_url
  item.unit = option.unit
  item.unit_price = option.unit_price
}

function validateForm() {
  if (!form.order_no) { ElMessage.warning('请填写订单号'); return false }
  if (!form.items?.length) { ElMessage.warning('请添加订单明细'); return false }
  if (form.items.some((item: Row) => Number(item.quantity) <= 0)) {
    ElMessage.warning('订单明细数量必须大于0')
    return false
  }
  return true
}

async function saveOrder() {
  if (!validateForm()) return
  saving.value = true
  try {
    const payload = {
      ...form,
      order_type: meta.value.apiType,
      order_date: form.order_date || null,
      expected_date: form.expected_date || null,
      items: (form.items || []).map(({ product_key, product_image_url, variant_image_url, ...item }: Row) => item),
    }
    if (editingId.value) await api.put(`/orders/${editingId.value}`, payload)
    else await api.post('/orders', payload)
    ElMessage.success(`订单已${editingId.value ? '修改' : '新建'}`)
    dialogVisible.value = false
    await loadOrders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '订单保存失败')
  } finally {
    saving.value = false
  }
}

async function changeStatus(row: Row, status: string) {
  try {
    if (status === '已完成' && row.status !== '已完成') {
      const typeText = row.order_type || meta.value.title
      const lines: string[] = []
      if (typeText.includes('租赁') || typeText.includes('租摆')) lines.push('租摆进场：按明细位置写入/增加项目植物。')
      if (typeText.includes('换花')) lines.push('换花：按明细位置记录更换，旧植物默认丢弃。')
      if (typeText.includes('撤花')) lines.push('撤花：按明细位置扣减项目植物，数量为 0 时标记已撤场。')
      if ((row.items || []).some((item: Row) => `${item.product_name || ''}${item.variant_name || ''}${item.notes || ''}`.includes('花盆') || `${item.notes || ''}${row.notes || ''}`.includes('换盆'))) {
        lines.push('花盆/换盆明细：只更新项目植物的花盆信息，不新增植物。')
      }
      if (lines.length) {
        await ElMessageBox.confirm(
          `确认将订单更新为“已完成”？\n\n${lines.join('\n')}\n\n请先确认明细里的楼层/区域/办公室填写正确。`,
          '完成订单并联动项目植物',
          { confirmButtonText: '确认完成', cancelButtonText: '再检查一下', type: 'warning' },
        )
      }
    }
    await api.post(`/orders/${row.id}/status`, { status })
    ElMessage.success(`订单已更新为${status}`)
    await loadOrders()
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(error.response?.data?.detail || '状态更新失败')
  }
}

async function createPurchase(row: Row) {
  try {
    const response = await api.post(`/orders/${row.id}/create-purchase`)
    const allocatedCount = Array.isArray(response.data.allocations) ? response.data.allocations.length : 0
    if (response.data.status === 'receipt_allocated' || response.data.status === 'stock_available') {
      ElMessage.success(response.data.message || '已优先匹配未安排收据余量，订单进入待配送')
      await loadOrders()
    } else {
      const prefix = allocatedCount ? `已匹配 ${allocatedCount} 条收据余量，` : ''
      ElMessage.success(response.data.status === 'exists' ? `采购单已存在：${response.data.purchase_order_no}` : `${prefix}缺口已生成采购单：${response.data.purchase_order_no}`)
      await loadOrders()
      if (response.data.purchase_order_no) {
        router.push({ path: '/module/purchase/list', query: { highlight: response.data.purchase_order_no } })
      }
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '库存/采购处理失败')
  }
}

function rowsForBatch(action: 'purchase' | 'delivery' | 'complete') {
  return selectedOrders.value.filter((row) => {
    const next = nextOrderAction(row)
    if (!next || next.disabled) return false
    if (action === 'purchase') return next.label === '采购'
    if (action === 'delivery') return next.label === '配送'
    return next.label === '完成'
  })
}

async function runBatchAction(action: 'purchase' | 'delivery' | 'complete') {
  const actionText = action === 'purchase' ? '采购' : action === 'delivery' ? '配送' : '完成'
  const rows = rowsForBatch(action)
  if (!selectedOrders.value.length) {
    ElMessage.warning('请先勾选需要处理的订单')
    return
  }
  if (!rows.length) {
    ElMessage.warning(`勾选的订单里没有可批量${actionText}的单据`)
    return
  }
  await ElMessageBox.confirm(
    `已勾选 ${selectedOrders.value.length} 条，其中 ${rows.length} 条可以批量${actionText}。确认继续吗？`,
    `批量${actionText}`,
    { type: 'warning', confirmButtonText: `确认${actionText}`, cancelButtonText: '取消' },
  )
  saving.value = true
  let successCount = 0
  let lastJump: { path: string; highlight: string } | null = null
  try {
    for (const row of rows) {
      if (action === 'purchase') {
        const response = await api.post(`/orders/${row.id}/create-purchase`)
        successCount += 1
        if (response.data.purchase_order_no) {
          lastJump = { path: '/module/purchase/list', highlight: response.data.purchase_order_no }
        }
      } else if (action === 'delivery') {
        const response = await api.post(`/orders/${row.id}/create-outbound`)
        successCount += 1
        if (response.data.outbound_order_no) {
          lastJump = { path: '/module/warehouse/list', highlight: response.data.outbound_order_no }
        }
      } else {
        await api.post(`/orders/${row.id}/status`, { status: '已完成' })
        successCount += 1
      }
    }
    ElMessage.success(`已批量${actionText} ${successCount} 条`)
    await loadOrders()
    if (lastJump) {
      router.push({ path: lastJump.path, query: { highlight: lastJump.highlight } })
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || `批量${actionText}失败，已处理 ${successCount} 条`)
    await loadOrders()
  } finally {
    saving.value = false
  }
}

async function createOutbound(row: Row) {
  try {
    const response = await api.post(`/orders/${row.id}/create-outbound`)
    ElMessage.success(response.data.status === 'exists' ? `出库单已存在：${response.data.outbound_order_no}` : `已生成出库单：${response.data.outbound_order_no}`)
    await loadOrders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '生成出库单失败')
  }
}

function enterPurchaseOrder(row: Row) {
  router.push({ path: '/module/purchase/list', query: { highlight: `CG-${row.order_no}` } })
}

async function enterDeliveryOrder(row: Row) {
  try {
    const response = await api.post(`/orders/${row.id}/create-outbound`)
    ElMessage.success(response.data.status === 'exists' ? `已进入配送订单：${response.data.outbound_order_no}` : `已生成配送订单：${response.data.outbound_order_no}`)
    await loadOrders()
    router.push({ path: '/module/warehouse/list', query: { highlight: response.data.outbound_order_no } })
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '进入配送订单失败')
  }
}

async function createSchedule(row: Row) {
  await loadScheduleOptions()
  resetScheduleForm({
    order_id: row.id,
    order_no: row.order_no,
    project_name: row.project_name,
    schedule_date: row.expected_date || row.order_date || new Date().toISOString().slice(0, 10),
    driver_id: null,
    assistant_ids: [],
    vehicle_id: null,
    notes: `由订单 ${row.order_no} 生成；联系人：${row.contact_phone || row.customer_name || ''}`,
  })
  scheduleVisible.value = true
}

async function submitSchedule() {
  if (!scheduleForm.order_id) return
  try {
    const payload = {
      schedule_date: scheduleForm.schedule_date || null,
      driver_id: scheduleForm.driver_id || null,
      assistant_ids: (scheduleForm.assistant_ids || []).join(','),
      vehicle_id: scheduleForm.vehicle_id || null,
      notes: scheduleForm.notes || '',
    }
    const response = await api.post(`/schedules/from-order/${scheduleForm.order_id}`, payload)
    ElMessage.success(response.data.status === 'exists' ? `安排已存在：${response.data.task_no}` : `已生成每日安排：${response.data.task_no}`)
    scheduleVisible.value = false
    await loadOrders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '生成每日安排失败')
  }
}

watch(() => route.fullPath, () => {
  keyword.value = ''
  loadColumnSetting()
  loadOrders()
})

loadColumnSetting()
loadBaseData()
loadOrders()
</script>

<template>
  <div class="page order-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">ORDER</p>
        <h1>{{ meta.title }}</h1>
        <p>{{ meta.desc }}</p>
      </div>
      <el-button type="success" :icon="Plus" @click="openCreate">新增{{ meta.title }}</el-button>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="搜索订单号、项目、客户、报单人" @keyup.enter="loadOrders" @clear="loadOrders" />
        <el-button type="success" plain :icon="Search" @click="loadOrders">查询</el-button>
        <el-button :icon="Refresh" @click="keyword=''; loadOrders()">重置</el-button>
        <div v-if="selectedOrders.length" class="batch-action-bar">
          <span>已选 {{ selectedOrders.length }} 条</span>
          <el-button size="small" type="warning" plain :loading="saving" @click="runBatchAction('purchase')">批量采购</el-button>
          <el-button size="small" type="primary" plain :loading="saving" @click="runBatchAction('delivery')">批量配送</el-button>
          <el-button size="small" type="success" plain :loading="saving" @click="runBatchAction('complete')">批量完成</el-button>
        </div>
      </div>
        <el-table v-loading="loading" :data="orders" stripe @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="46" fixed="left" />
        <el-table-column v-if="showColumn('order_no')" prop="order_no" label="订单号" min-width="135" />
        <el-table-column v-if="showColumn('project_name')" prop="project_name" label="项目" min-width="150" />
        <el-table-column v-if="showColumn('customer_name')" prop="customer_name" label="客户" min-width="130" />
        <el-table-column v-if="showColumn('requester')" prop="requester" label="报单/接单人" width="110" />
        <el-table-column v-if="showColumn('order_date')" prop="order_date" label="下单日期" width="110" />
        <el-table-column v-if="showColumn('expected_date')" prop="expected_date" label="期望完成" width="110" />
        <el-table-column v-if="showColumn('items')" label="明细" min-width="240"><template #default="scope">{{ itemSummary(scope.row) }}</template></el-table-column>
        <el-table-column v-if="showColumn('amount')" label="金额" width="105"><template #default="scope">¥{{ orderTotal(scope.row).toFixed(2) }}</template></el-table-column>
        <el-table-column v-if="showColumn('priority')" prop="priority" label="优先级" width="82" />
        <el-table-column v-if="showColumn('flow')" label="流程" width="118">
          <template #default="scope">
            <el-tag v-if="scope.row.need_purchase" size="small" type="warning">需采购</el-tag>
            <el-tag v-if="scope.row.need_delivery" size="small" type="success" class="tag-gap">需配送</el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="showColumn('current_step')" label="当前步骤" min-width="180">
          <template #default="scope">
            <div class="order-current-step">
              <el-tag :type="currentStepTagType(scope.row)" size="small" effect="light">{{ displayOrderStatus(scope.row.current_step || scope.row.status) }}</el-tag>
              <span>{{ displayOrderStatus(scope.row.current_status || scope.row.status) }}</span>
              <small v-if="scope.row.current_actor || scope.row.current_ref_no">
                {{ scope.row.current_actor || '相关人员' }}<template v-if="scope.row.current_ref_no"> · {{ scope.row.current_ref_no }}</template>
              </small>
            </div>
          </template>
        </el-table-column>
        <el-table-column v-if="showColumn('progress')" label="流程进度" min-width="260">
          <template #default="scope">
            <div class="progress-tags">
              <el-tag
                v-for="node in scope.row.progress || []"
                :key="node.key"
                size="small"
                :type="progressTagType(node)"
                effect="plain"
              >
                {{ node.label }}：{{ node.status }}
              </el-tag>
              <el-button v-if="(scope.row.progress || []).length" link type="primary" size="small" @click="openProgress(scope.row)">详情</el-button>
              <span v-if="!(scope.row.progress || []).length" class="muted">无后续流程</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column v-if="showColumn('status')" label="状态" width="94"><template #default="scope"><el-tag :type="statusTagType(scope.row.status)">{{ displayOrderStatus(scope.row.status) }}</el-tag></template></el-table-column>
        <el-table-column label="操作" fixed="right" width="178">
          <template #default="scope">
            <div class="order-row-actions">
              <el-button
                v-if="nextOrderAction(scope.row)"
                size="small"
                :type="nextOrderAction(scope.row)?.type"
                :disabled="nextOrderAction(scope.row)?.disabled"
                @click="nextOrderAction(scope.row)?.handler()"
              >
                {{ nextOrderAction(scope.row)?.label }}
              </el-button>
              <el-dropdown trigger="click">
                <el-button link type="primary" class="table-more-button">更多<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="openDetail(scope.row)">查看详情</el-dropdown-item>
                    <el-dropdown-item :disabled="['已完成','已取消'].includes(scope.row.status)" @click="openEdit(scope.row)">编辑订单</el-dropdown-item>
                    <el-dropdown-item :disabled="!(scope.row.progress || []).length" @click="openProgress(scope.row)">流程详情</el-dropdown-item>
                    <el-dropdown-item :disabled="scope.row.status === '已完成'" @click="changeStatus(scope.row, '已完成')">手动完成</el-dropdown-item>
                    <el-dropdown-item :disabled="scope.row.status === '已取消'" divided @click="changeStatus(scope.row, '已取消')">取消订单</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <el-dialog v-model="columnSettingVisible" title="表头显示设置" width="460px" destroy-on-close>
      <div class="column-setting-box">
        <p>勾选当前账号在“{{ meta.title }}”列表里需要显示的表头，不会影响其他账号。</p>
        <el-checkbox-group v-model="visibleColumnKeys" class="column-setting-grid">
          <el-checkbox v-for="item in orderColumns" :key="item.key" :label="item.key">{{ item.label }}</el-checkbox>
        </el-checkbox-group>
      </div>
      <template #footer>
        <el-button @click="visibleColumnKeys=[...defaultColumnKeys]">恢复默认</el-button>
        <el-button @click="columnSettingVisible=false">取消</el-button>
        <el-button type="success" @click="saveColumnSetting">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dialogVisible" :title="`${editingId ? '编辑' : '新增'}${meta.title}`" width="92%" top="5vh" destroy-on-close>
      <el-form label-position="top" class="purchase-form">
        <section class="form-section">
          <div class="form-grid four">
            <el-form-item label="订单号" required><el-input v-model="form.order_no" /></el-form-item>
            <el-form-item label="项目">
              <el-select v-model="form.project_id" filterable clearable placeholder="可选项目" style="width:100%" @change="handleProjectChange">
                <el-option v-for="project in projects" :key="project.id" :label="`${project.name} · ${project.customer_name || '未关联客户'}`" :value="project.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="客户">
              <el-select v-model="form.customer_id" filterable clearable placeholder="可选客户" style="width:100%" @change="handleCustomerChange">
                <el-option v-for="customer in customers" :key="customer.id" :label="`${customer.name}${customer.project_name ? ' · ' + customer.project_name : ''}`" :value="customer.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="报单/接单人"><el-input v-model="form.requester" /></el-form-item>
            <el-form-item label="联系电话"><el-input v-model="form.contact_phone" /></el-form-item>
            <el-form-item label="下单日期"><el-date-picker v-model="form.order_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
            <el-form-item label="期望完成"><el-date-picker v-model="form.expected_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
            <el-form-item label="优先级"><el-select v-model="form.priority" style="width:100%"><el-option label="普通" value="普通" /><el-option label="紧急" value="紧急" /></el-select></el-form-item>
            <el-form-item label="是否需要采购"><el-switch v-model="form.need_purchase" active-text="需要" inactive-text="不需要" /></el-form-item>
            <el-form-item label="是否需要配送"><el-switch v-model="form.need_delivery" active-text="需要" inactive-text="不需要" /></el-form-item>
            <el-form-item label="状态"><el-select v-model="form.status" style="width:100%"><el-option label="待处理" value="待处理" /><el-option label="处理中" value="处理中" /><el-option label="已完成" value="已完成" /><el-option label="已取消" value="已取消" /></el-select></el-form-item>
            <el-form-item label="备注" class="wide"><el-input v-model="form.notes" type="textarea" :rows="2" /></el-form-item>
          </div>
        </section>

        <section class="form-section purchase-items-section">
          <div class="section-title"><strong>订单明细</strong><span>选择商品时直接带出规格、图片、单位和参考价格，也可填写摆放位置/更换位置</span><el-button link type="success" :icon="Plus" @click="addItem">添加明细</el-button></div>
          <div class="purchase-item-table order-item-table">
            <div class="purchase-item-row order-item-row purchase-item-header"><div>图片</div><div>商品名称</div><div>规格</div><div>位置</div><div>数量</div><div>单位</div><div>单价</div><div>金额</div><div>备注</div><div>操作</div></div>
            <div v-for="(item,index) in form.items" :key="index" class="purchase-item-row order-item-row">
              <div>
                <el-image v-if="itemImage(item)" class="order-item-image" :src="itemImage(item)" fit="cover" />
                <div v-else class="order-item-empty-image">无图</div>
              </div>
              <div>
                <el-select v-model="item.product_key" filterable clearable placeholder="选择商品/规格" @change="()=>handleProductChange(item)">
                  <template #label>{{ item.product_name || '' }}</template>
                  <el-option v-for="option in productOptions" :key="option.key" :label="option.label" :value="option.key">
                    <div class="order-product-option">
                      <el-image v-if="option.image_url" :src="option.image_url" fit="cover" />
                      <div v-else class="order-product-option-empty">无图</div>
                      <span>{{ option.label }}</span>
                    </div>
                  </el-option>
                </el-select>
              </div>
              <div class="order-item-spec-text">{{ item.variant_name || '-' }}</div>
              <div><el-input v-model="item.location_text" placeholder="楼层/区域/办公室" /></div>
              <div><el-input-number v-model="item.quantity" :min="0.01" :controls="false" /></div>
              <div><el-input v-model="item.unit" /></div>
              <div><el-input-number v-model="item.unit_price" :min="0" :controls="false" /></div>
              <div>¥{{ (Number(item.quantity || 0) * Number(item.unit_price || 0)).toFixed(2) }}</div>
              <div><el-input v-model="item.notes" /></div>
              <div><el-button link type="danger" @click="removeItem(index)">删除</el-button></div>
            </div>
          </div>
        </section>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="success" :loading="saving" @click="saveOrder">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="订单详情" width="1120px" top="5vh" destroy-on-close>
      <div v-if="detailOrder" class="order-detail document-detail">
        <section class="document-card">
          <div class="document-title">
            <strong>详细信息</strong>
            <span>{{ meta.title }} · {{ detailOrder.order_no }}</span>
          </div>
          <table class="document-info-table">
            <tbody>
              <tr v-for="(row, rowIndex) in orderDocumentRows(detailOrder)" :key="rowIndex">
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
            <span>按摆放位置列出，后面可直接用于打印和交付确认</span>
          </div>
          <el-table :data="detailOrder.items || []" border class="document-plant-table">
            <el-table-column prop="product_name" label="名称" min-width="150" />
            <el-table-column label="产品图" width="115">
              <template #default="scope">
                <el-image v-if="itemImage(scope.row)" class="document-product-image" :src="itemImage(scope.row)" fit="cover" />
                <div v-else class="document-product-empty">无图</div>
              </template>
            </el-table-column>
            <el-table-column label="规格" min-width="130">
              <template #default="scope">{{ scope.row.variant_name || '-' }}</template>
            </el-table-column>
            <el-table-column prop="unit" label="单位" width="80" />
            <el-table-column label="数量" width="90">
              <template #default="scope">{{ formatNumber(scope.row.quantity) }}</template>
            </el-table-column>
            <el-table-column label="单价/元" width="105">
              <template #default="scope">{{ moneyText(scope.row.unit_price) }}</template>
            </el-table-column>
            <el-table-column label="金额/元" width="115">
              <template #default="scope">{{ moneyText(itemAmount(scope.row)) }}</template>
            </el-table-column>
            <el-table-column label="摆放位置" min-width="170">
              <template #default="scope">{{ scope.row.location_text || '-' }}</template>
            </el-table-column>
          </el-table>
        </section>

        <section class="order-detail-section">
          <h3>流程进度</h3>
          <el-table :data="detailOrder.progress || []" border empty-text="无后续流程">
            <el-table-column prop="label" label="节点" width="90" />
            <el-table-column label="状态" width="100">
              <template #default="scope"><el-tag :type="progressTagType(scope.row)" size="small">{{ scope.row.status }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="ref_no" label="关联单号" min-width="145" />
            <el-table-column prop="actor" label="处理人" width="95">
              <template #default="scope">{{ scope.row.actor || '-' }}</template>
            </el-table-column>
            <el-table-column prop="date" label="日期" width="105">
              <template #default="scope">{{ scope.row.date || '-' }}</template>
            </el-table-column>
            <el-table-column prop="description" label="说明" min-width="170" show-overflow-tooltip />
          </el-table>
        </section>
      </div>
      <template #footer>
        <el-button type="success" @click="detailVisible=false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="progressVisible" title="流程详情" width="760px" destroy-on-close>
      <div v-if="progressOrder" class="progress-detail">
        <div class="progress-detail-head">
          <div><span>订单号</span><strong>{{ progressOrder.order_no }}</strong></div>
          <div><span>项目</span><strong>{{ progressOrder.project_name || '-' }}</strong></div>
          <div><span>当前状态</span><strong>{{ progressOrder.status }}</strong></div>
        </div>
        <el-table :data="progressOrder.progress || []" border>
          <el-table-column prop="label" label="节点" width="90" />
          <el-table-column label="状态" width="100">
            <template #default="scope"><el-tag :type="progressTagType(scope.row)" size="small">{{ scope.row.status }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="ref_no" label="关联单号" min-width="145" />
          <el-table-column prop="actor" label="处理人" width="95">
            <template #default="scope">{{ scope.row.actor || '-' }}</template>
          </el-table-column>
          <el-table-column prop="date" label="日期" width="105">
            <template #default="scope">{{ scope.row.date || '-' }}</template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="170" show-overflow-tooltip />
        </el-table>
      </div>
      <template #footer>
        <el-button type="success" @click="progressVisible=false">知道了</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="scheduleVisible" title="指派配送" width="760px" destroy-on-close>
      <el-form label-position="top" class="purchase-form">
        <div class="form-grid four">
          <el-form-item label="来源订单"><el-input v-model="scheduleForm.order_no" disabled /></el-form-item>
          <el-form-item label="项目"><el-input v-model="scheduleForm.project_name" disabled /></el-form-item>
          <el-form-item label="配送日期"><el-date-picker v-model="scheduleForm.schedule_date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
          <div class="dispatch-assignment-row">
            <el-form-item label="指定车辆">
              <el-select v-model="scheduleForm.vehicle_id" filterable clearable style="width:100%" placeholder="可不选">
                <el-option v-for="vehicle in vehicles" :key="vehicle.id" :label="vehicle.plate_no" :value="vehicle.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="司机">
              <el-select v-model="scheduleForm.driver_id" filterable clearable style="width:100%" placeholder="选择司机">
                <el-option v-for="employee in employees" :key="employee.id" :label="employee.name" :value="employee.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="跟车/配送人员">
              <el-select v-model="scheduleForm.assistant_ids" multiple filterable clearable collapse-tags style="width:100%" placeholder="可多选">
                <el-option v-for="employee in employees" :key="employee.id" :label="employee.name" :value="employee.id" />
              </el-select>
            </el-form-item>
          </div>
          <el-form-item label="备注" class="wide"><el-input v-model="scheduleForm.notes" /></el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="scheduleVisible=false">取消</el-button>
        <el-button type="success" :loading="saving" @click="submitSchedule">生成配送安排</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.order-row-actions {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  width: 100%;
}

.order-row-actions :deep(.el-button--small) {
  min-width: 92px;
  padding-inline: 10px;
}

.batch-action-bar {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border: 1px solid #d9ecff;
  border-radius: 999px;
  background: #f4f9ff;
  color: #2b5f96;
  font-size: 13px;
  white-space: nowrap;
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
</style>
