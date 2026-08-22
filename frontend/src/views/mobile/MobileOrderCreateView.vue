<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ArrowLeft, Check, Plus, Refresh, Remove } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { api } from '../../api/client'

type Row = Record<string, any>

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const projects = ref<Row[]>([])
const products = ref<Row[]>([])
const variantMap = reactive<Record<number, Row[]>>({})

const form = reactive<Row>({
  order_type: 'lease',
  project_id: null,
  customer_name: '',
  contact_phone: '',
  expected_date: '',
  priority: '普通',
  need_purchase: true,
  need_delivery: true,
  notes: '',
  items: [{ product_id: null, variant_id: null, product_name: '', variant_name: '', quantity: 1, unit: '盆', location_text: '', unit_price: null }],
})

const selectedProject = computed(() => projects.value.find((item) => item.id === form.project_id))
const currentProjectCategory = computed(() => {
  if (String(form.order_type || '').startsWith('engineering')) return '工程绿化'
  if (String(form.order_type || '').startsWith('grid')) return '电网'
  if (String(form.order_type || '').startsWith('cleaning')) return '保洁'
  return '租摆'
})
const selectableProducts = computed(() => products.value.filter((product) => {
  const categories = String(product.project_categories || '').split(',').map((item) => item.trim()).filter(Boolean)
  return !categories.length || categories.includes(currentProjectCategory.value)
}))
const selectableProjects = computed(() => projects.value.filter((project) => {
  const businesses = String(project.business_types || project.business_type || '').split(',').map((item) => item.trim()).filter(Boolean)
  return !businesses.length || businesses.includes(currentProjectCategory.value)
}))

const orderTypeOptions = [
  { label: '租摆订单', value: 'lease' },
  { label: '销售订单', value: 'sales' },
  { label: '赠送订单', value: 'gift' },
  { label: '撤花订单', value: 'withdraw' },
  { label: '工程订单', value: 'engineering' },
  { label: '工程物料', value: 'engineering-material' },
  { label: '电网绿风', value: 'grid-greenwind' },
  { label: '电网盛景', value: 'grid-shengjing' },
  { label: '保洁订单', value: 'cleaning' },
  { label: '保洁物料', value: 'cleaning-material' },
]

function unitPrice(product: Row, variant?: Row) {
  if (form.order_type === 'grid-greenwind') return variant?.grid_greenwind_price || product.grid_greenwind_price || variant?.sale_price || product.sale_price || 0
  if (form.order_type === 'grid-shengjing') return variant?.grid_shengjing_price || product.grid_shengjing_price || variant?.sale_price || product.sale_price || 0
  if (['lease', 'exchange'].includes(form.order_type)) return variant?.monthly_rental_price || product.monthly_rental_price || variant?.sale_price || product.sale_price || 0
  return variant?.sale_price || product.sale_price || variant?.monthly_rental_price || product.monthly_rental_price || 0
}

function orderNo() {
  const prefixes: Record<string, string> = { lease: 'ZB', sales: 'XS', gift: 'ZS', withdraw: 'CH', engineering: 'GC', 'engineering-material': 'GW', 'grid-greenwind': 'DL', 'grid-shengjing': 'DS', cleaning: 'BJ', 'cleaning-material': 'BW' }
  return `${prefixes[form.order_type] || 'SJ'}${Date.now().toString().slice(-6)}`
}

async function loadData() {
  loading.value = true
  try {
    const [projectRes, productRes] = await Promise.all([api.get('/projects'), api.get('/products')])
    projects.value = projectRes.data.items || []
    products.value = productRes.data.items || []
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '下单数据加载失败')
  } finally {
    loading.value = false
  }
}

async function loadVariants(productId: number | null) {
  if (!productId || variantMap[productId]) return
  const response = await api.get(`/products/${productId}/variants`)
  variantMap[productId] = response.data.items || []
}

async function productChanged(row: Row) {
  row.variant_id = null
  const product = products.value.find((item) => item.id === row.product_id)
  row.product_name = product?.name || ''
  row.unit = product?.project_unit || product?.unit || '盆'
  row.unit_price = product ? unitPrice(product) : null
  if (row.product_id) await loadVariants(row.product_id)
}

function variantChanged(row: Row) {
  const variants = variantMap[row.product_id] || []
  const variant = variants.find((item) => item.id === row.variant_id)
  row.variant_name = variant?.specification || ''
  row.unit = variant?.unit || row.unit
  const product = products.value.find((item) => item.id === row.product_id)
  row.unit_price = product ? unitPrice(product, variant) : row.unit_price
}

function projectChanged() {
  const project = selectedProject.value
  if (!project) return
  form.customer_name = project.customer_name || form.customer_name
}

function addItem() {
  form.items.push({ product_id: null, variant_id: null, product_name: '', variant_name: '', quantity: 1, unit: '盆', location_text: '', unit_price: null })
}

function removeItem(index: number) {
  if (form.items.length === 1) return
  form.items.splice(index, 1)
}

async function submit() {
  if (!form.project_id) {
    ElMessage.warning('请选择项目')
    return
  }
  const validItems = form.items.filter((item: Row) => item.product_id && Number(item.quantity || 0) > 0)
  if (!validItems.length) {
    ElMessage.warning('请至少选择一个商品')
    return
  }
  saving.value = true
  try {
    const project = selectedProject.value
    const payload = {
      order_no: orderNo(),
      order_type: form.order_type,
      project_id: form.project_id,
      project_name: project?.name || '',
      customer_name: form.customer_name || project?.customer_name || project?.name || '',
      requester: JSON.parse(localStorage.getItem('greenwind_user') || '{}')?.display_name || '手机端',
      contact_phone: form.contact_phone || '',
      order_date: new Date().toISOString().slice(0, 10),
      expected_date: form.expected_date || null,
      priority: form.priority,
      need_purchase: Boolean(form.need_purchase),
      need_delivery: Boolean(form.need_delivery),
      status: '待处理',
      notes: form.notes || '手机端快速下单',
      items: validItems.map((item: Row) => ({
        product_id: item.product_id,
        variant_id: item.variant_id,
        product_name: item.product_name,
        variant_name: item.variant_name,
        location_text: item.location_text,
        quantity: Number(item.quantity || 1),
        unit: item.unit || '盆',
        unit_price: Number(item.unit_price || 0),
        notes: '',
      })),
    }
    const response = await api.post('/orders', payload)
    ElMessage.success(`订单已提交：${response.data.order_no}`)
    router.push('/mobile')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '手机下单失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
watch(() => form.order_type, () => {
  if (form.project_id && !selectableProjects.value.some((project) => project.id === form.project_id)) form.project_id = null
  form.items.forEach((item: Row) => {
    if (item.product_id && !selectableProducts.value.some((product) => product.id === item.product_id)) {
      Object.assign(item, { product_id: null, variant_id: null, product_name: '', variant_name: '', unit_price: null })
    }
  })
})
</script>

<template>
  <div class="mobile-page mobile-create-page" v-loading="loading">
    <section class="mobile-title compact-title">
      <button type="button" @click="router.back()"><el-icon><ArrowLeft /></el-icon></button>
      <div><p>ORDER</p><h1>手机下单</h1></div>
      <button type="button" @click="loadData"><el-icon><Refresh /></el-icon></button>
    </section>

    <section class="mobile-form-card pretty compact-form">
      <el-form label-position="top">
        <el-form-item label="订单类型">
          <el-select v-model="form.order_type" placeholder="选择业务订单类型">
            <el-option v-for="item in orderTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目" required>
          <el-select v-model="form.project_id" filterable clearable placeholder="选择项目" @change="projectChanged">
            <el-option v-for="project in selectableProjects" :key="project.id" :label="`${project.name} · ${project.customer_name || '未关联客户'}`" :value="project.id" />
          </el-select>
        </el-form-item>
        <div class="mobile-inline-two">
          <el-form-item label="联系人/客户">
            <el-input v-model="form.customer_name" placeholder="可空，默认项目客户" />
          </el-form-item>
          <el-form-item label="联系电话">
            <el-input v-model="form.contact_phone" placeholder="可空" />
          </el-form-item>
        </div>

        <div class="mobile-order-items">
          <div v-for="(row, index) in form.items" :key="index" class="mobile-order-item">
            <div class="mobile-order-item-head">
              <strong>商品 {{ Number(index) + 1 }}</strong>
              <button type="button" @click="removeItem(Number(index))"><el-icon><Remove /></el-icon></button>
            </div>
            <el-form-item label="商品">
              <el-select v-model="row.product_id" filterable placeholder="选择商品" @change="productChanged(row)">
                <el-option v-for="product in selectableProducts" :key="product.id" :label="product.name" :value="product.id" />
              </el-select>
            </el-form-item>
            <div class="mobile-inline-two">
              <el-form-item label="规格">
                <el-select v-model="row.variant_id" clearable filterable placeholder="可不选" @change="variantChanged(row)">
                  <el-option v-for="variant in (variantMap[row.product_id] || [])" :key="variant.id" :label="variant.specification || variant.code" :value="variant.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="位置">
                <el-input v-model="row.location_text" placeholder="楼层/区域" />
              </el-form-item>
            </div>
            <div class="mobile-inline-two">
              <el-form-item label="数量">
                <el-input-number v-model="row.quantity" :min="1" :precision="0" :controls="false" />
              </el-form-item>
              <el-form-item label="单位">
                <el-input v-model="row.unit" />
              </el-form-item>
            </div>
          </div>
          <button type="button" class="mobile-add-line" @click="addItem"><el-icon><Plus /></el-icon>继续添加商品</button>
        </div>

        <div class="mobile-inline-two">
          <el-form-item label="期望日期">
            <el-date-picker v-model="form.expected_date" value-format="YYYY-MM-DD" clearable />
          </el-form-item>
          <el-form-item label="优先级">
            <el-select v-model="form.priority">
              <el-option v-for="item in ['普通','加急','重要']" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="流程需要">
          <div class="mobile-check-row">
            <el-checkbox v-model="form.need_purchase">需要采购</el-checkbox>
            <el-checkbox v-model="form.need_delivery">需要配送</el-checkbox>
          </div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="现场要求、联系人说明等" />
        </el-form-item>
        <el-button class="mobile-submit gradient" type="success" :loading="saving" :icon="Check" @click="submit">提交订单</el-button>
      </el-form>
    </section>
  </div>
</template>
