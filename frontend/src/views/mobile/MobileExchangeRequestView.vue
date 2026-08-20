<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Check, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../../api/client'

type Row = Record<string, any>

const loading = ref(false)
const saving = ref(false)
const projects = ref<Row[]>([])
const products = ref<Row[]>([])
const productOptions = ref<Row[]>([])
const variantCache = reactive<Record<number, Row[]>>({})
const recentOrders = ref<Row[]>([])
const form = reactive<Row>({
  request_type: '换花',
  project_id: null,
  product_key: '',
  product_id: null,
  variant_id: null,
  location_text: '',
  product_name: '',
  variant_name: '',
  quantity: 1,
  unit: '盆',
  reason: '',
  expected_date: '',
  priority: '普通',
  need_purchase: true,
  need_delivery: true,
  notes: '',
})

async function loadData() {
  loading.value = true
  try {
    const [projectRes, productRes, orderRes] = await Promise.all([
      api.get('/projects'),
      api.get('/products'),
      api.get('/orders', { params: { order_type: 'exchange' } }),
    ])
    projects.value = projectRes.data.items || []
    products.value = productRes.data.items || []
    await Promise.all(products.value.map((product) => loadVariants(product.id)))
    productOptions.value = buildProductOptions()
    recentOrders.value = orderRes.data.items || []
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '报单数据加载失败')
  } finally {
    loading.value = false
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

async function loadVariants(productId: number | string | null) {
  const key = Number(productId)
  if (!key || variantCache[key]) return
  variantCache[key] = (await api.get(`/products/${key}/variants`)).data.items || []
}

function buildProductOptions() {
  return products.value.flatMap((product) => {
    const variants = variantCache[product.id] || []
    if (!variants.length) {
      return [{
        key: `${product.id}:`,
        product_id: product.id,
        variant_id: null,
        label: `${product.name}${product.specification ? ' · ' + product.specification : ''}`,
        product_name: product.name,
        variant_name: product.specification || '',
        unit: product.project_unit || product.unit || '盆',
      }]
    }
    return variants.map((variant) => ({
      key: `${product.id}:${variant.id}`,
      product_id: product.id,
      variant_id: variant.id,
      label: `${product.name} · ${variantLabel(variant)}`,
      product_name: product.name,
      variant_name: variantLabel(variant),
      unit: variant.unit || product.project_unit || product.unit || '盆',
    }))
  })
}

function handleProductSelect() {
  const option = productOptions.value.find((entry) => entry.key === form.product_key)
  if (!option) {
    form.product_id = null
    form.variant_id = null
    form.product_name = String(form.product_key || '')
    return
  }
  form.product_id = option.product_id
  form.variant_id = option.variant_id
  form.product_name = option.product_name
  form.variant_name = option.variant_name
  form.unit = option.unit
}

function resetAfterSave() {
  form.product_key = ''
  form.product_id = null
  form.variant_id = null
  form.location_text = ''
  form.product_name = ''
  form.variant_name = ''
  form.quantity = 1
  form.reason = ''
  form.expected_date = ''
  form.notes = ''
}

async function submit() {
  if (!form.project_id) {
    ElMessage.warning('请选择项目')
    return
  }
  if (!form.location_text) {
    ElMessage.warning('请填写楼层/区域/办公室位置')
    return
  }
  if (!form.product_name) {
    ElMessage.warning('请填写要更换的植物或花盆')
    return
  }
  saving.value = true
  try {
    const response = await api.post('/orders/mobile-exchange-request', form)
    ElMessage.success(`已提交：${response.data.order_no}`)
    resetAfterSave()
    await loadData()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '报单提交失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="mobile-page mobile-exchange-page" v-loading="loading">
    <section class="mobile-title">
      <div><p>REQUEST</p><h1>报换花/换盆</h1></div>
      <button type="button" @click="loadData"><el-icon><Refresh /></el-icon></button>
    </section>

    <section class="mobile-soft-banner">
      <strong>养护现场发现问题，直接手机报单</strong>
      <span>提交后会进入电脑后台的“换花订单”，客服可继续采购、派单、配送。</span>
    </section>

    <section class="mobile-form-card pretty">
      <el-form label-position="top">
        <el-form-item label="报单类型">
          <el-segmented v-model="form.request_type" :options="['换花','换盆','补植物','其他']" />
        </el-form-item>
        <el-form-item label="项目" required>
          <el-select v-model="form.project_id" filterable clearable placeholder="请选择项目">
            <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="楼层/区域/办公室" required>
          <el-input v-model="form.location_text" placeholder="例如：A栋8楼总经理办公室" />
        </el-form-item>
        <div class="mobile-inline-two">
          <el-form-item label="植物/花盆" required>
            <el-select
              v-model="form.product_key"
              filterable
              clearable
              allow-create
              default-first-option
              placeholder="选择商品或直接输入"
              @change="handleProductSelect"
            >
              <el-option v-for="option in productOptions" :key="option.key" :label="option.label" :value="option.key" />
            </el-select>
            <el-input v-if="!form.product_id" v-model="form.product_name" class="manual-product-input" placeholder="例如：小绿萝 / 福字盆" />
          </el-form-item>
          <el-form-item label="规格/型号">
            <el-input v-model="form.variant_name" placeholder="例如：180# / 中号" />
          </el-form-item>
        </div>
        <div class="mobile-inline-two narrow">
          <el-form-item label="数量">
            <el-input-number v-model="form.quantity" :min="1" :precision="0" />
          </el-form-item>
          <el-form-item label="单位">
            <el-select v-model="form.unit">
              <el-option v-for="unit in ['盆','个','棵','套','瓶','袋']" :key="unit" :label="unit" :value="unit" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="原因/现场说明">
          <el-input v-model="form.reason" type="textarea" :rows="3" placeholder="例如：叶片发黄、植物死亡、花盆破损、领导要求更换" />
        </el-form-item>
        <el-form-item label="期望完成日期">
          <el-date-picker v-model="form.expected_date" value-format="YYYY-MM-DD" clearable />
        </el-form-item>
        <el-form-item label="流程需要">
          <div class="mobile-check-row">
            <el-checkbox v-model="form.need_purchase">需要采购</el-checkbox>
            <el-checkbox v-model="form.need_delivery">需要配送</el-checkbox>
          </div>
        </el-form-item>
        <el-button class="mobile-submit gradient" type="success" :loading="saving" :icon="Check" @click="submit">提交报单</el-button>
      </el-form>
    </section>

    <section class="mobile-card">
      <div class="mobile-section-title"><strong>最近换花单</strong></div>
      <div v-if="recentOrders.length" class="mobile-list">
        <article v-for="row in recentOrders.slice(0, 5)" :key="row.id">
          <strong>{{ row.project_name || row.order_no }}</strong>
          <span>{{ row.order_no }}｜{{ row.status }}｜{{ row.expected_date || '未定日期' }}</span>
          <small>{{ (row.items || []).map((item: Row) => `${item.product_name}${item.variant_name ? ' ' + item.variant_name : ''} × ${item.quantity}${item.unit}`).join('，') }}</small>
        </article>
      </div>
      <el-empty v-else description="暂无换花单" :image-size="70" />
    </section>
  </div>
</template>

<style scoped>
.manual-product-input {
  margin-top: 8px;
}
</style>
