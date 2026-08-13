<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ArrowLeft, Check, Picture, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { api } from '../../api/client'

const router = useRouter()
const saving = ref(false)
const categoryDialog = ref(false)
const newCategory = ref('')
const categories = ref<string[]>([])

const form = reactive({
  name: '',
  category: '植物',
  code: '',
  specification: '',
  unit: '盆',
  reference_purchase_price: null as number | null,
  sale_price: null as number | null,
  monthly_rental_price: null as number | null,
  stock: null as number | null,
  image_url: '',
})

function autoCode() {
  if (!form.code) form.code = `SP-${Date.now().toString().slice(-8)}`
}

async function loadCategories() {
  try {
    const response = await api.get('/products/categories')
    categories.value = response.data.items || []
    if (!categories.value.includes(form.category) && categories.value.length) form.category = categories.value[0]
  } catch {
    categories.value = ['植物', '花盆', '农药', '肥料', '工具', '其他']
  }
}

async function addCategory() {
  const name = newCategory.value.trim()
  if (!name) {
    ElMessage.warning('请填写分类名称')
    return
  }
  try {
    await api.post('/products/categories', { name })
    ElMessage.success('分类已添加')
    newCategory.value = ''
    categoryDialog.value = false
    await loadCategories()
    form.category = name
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '添加分类失败')
  }
}

async function submit() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写商品名称')
    return
  }
  autoCode()
  saving.value = true
  try {
    const payload = {
      code: form.code,
      name: form.name,
      category: form.category || '未分类',
      specification: form.specification || '',
      unit: form.unit || '盆',
      purchase_unit: form.unit || '盆',
      base_unit: form.unit || '盆',
      project_unit: form.unit || '盆',
      conversion_rate: 1,
      project_conversion_rate: 1,
      reference_purchase_price: Number(form.reference_purchase_price || 0),
      sale_price: Number(form.sale_price || 0),
      monthly_rental_price: Number(form.monthly_rental_price || 0),
      stock: Number(form.stock || 0),
      image_url: form.image_url || '',
      image_urls: form.image_url ? JSON.stringify([form.image_url]) : '',
      specification_items: form.specification || '',
      replacement_cost_price: 0,
      min_sale_price: 0,
      package_conversion_enabled: false,
      status: '启用',
    }
    const product = (await api.post('/products', payload)).data
    if (form.specification.trim()) {
      await api.post(`/products/${product.id}/variants`, {
        code: `${form.code}-01`,
        specification: form.specification,
        specification_values: form.specification,
        image_url: form.image_url || '',
        unit: form.unit || '盆',
        is_default: true,
        sort_order: 1,
        conversion_quantity: 1,
        reference_purchase_price: Number(form.reference_purchase_price || 0),
        sale_price: Number(form.sale_price || 0),
        monthly_rental_price: Number(form.monthly_rental_price || 0),
        replacement_cost_price: 0,
        min_sale_price: 0,
        stock: Number(form.stock || 0),
        status: '启用',
      })
    }
    ElMessage.success('商品已新建')
    router.push('/mobile')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '新建商品失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadCategories)
</script>

<template>
  <div class="mobile-page mobile-create-page">
    <section class="mobile-title compact-title">
      <button type="button" @click="router.back()"><el-icon><ArrowLeft /></el-icon></button>
      <div><p>GOODS</p><h1>新建商品</h1></div>
    </section>

    <section class="mobile-form-card pretty compact-form">
      <div class="mobile-product-head">
        <div class="mobile-product-image">
          <img v-if="form.image_url" :src="form.image_url" alt="商品图片" />
          <div v-else><el-icon><Picture /></el-icon><span>商品图片</span></div>
        </div>
        <div class="mobile-product-main">
          <el-form label-position="top">
            <el-form-item label="商品名称" required>
              <el-input v-model="form.name" placeholder="例如：小绿萝" @blur="autoCode" />
            </el-form-item>
            <el-form-item label="图片地址">
              <el-input v-model="form.image_url" placeholder="粘贴图片地址" />
            </el-form-item>
          </el-form>
        </div>
      </div>

      <el-form label-position="top">
        <div class="mobile-inline-two">
          <el-form-item label="分类">
            <div class="mobile-select-with-action">
              <el-select v-model="form.category" filterable placeholder="选择分类">
                <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
              </el-select>
              <button type="button" @click="categoryDialog=true"><el-icon><Plus /></el-icon></button>
            </div>
          </el-form-item>
          <el-form-item label="单位">
            <el-select v-model="form.unit">
              <el-option v-for="item in ['盆','个','棵','套','瓶','袋','斤','箱']" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
        </div>
        <div class="mobile-inline-two">
          <el-form-item label="规格">
            <el-input v-model="form.specification" placeholder="180# / 中号 / 1.8m" />
          </el-form-item>
          <el-form-item label="商品编号">
            <el-input v-model="form.code" placeholder="不填自动生成" />
          </el-form-item>
        </div>
        <div class="mobile-inline-two">
          <el-form-item label="采购价">
            <el-input-number v-model="form.reference_purchase_price" :min="0" :precision="2" :controls="false" placeholder="可空" />
          </el-form-item>
          <el-form-item label="库存">
            <el-input-number v-model="form.stock" :min="0" :precision="0" :controls="false" placeholder="可空" />
          </el-form-item>
        </div>
        <div class="mobile-inline-two">
          <el-form-item label="销售价">
            <el-input-number v-model="form.sale_price" :min="0" :precision="2" :controls="false" placeholder="可空" />
          </el-form-item>
          <el-form-item label="月租价">
            <el-input-number v-model="form.monthly_rental_price" :min="0" :precision="2" :controls="false" placeholder="可空" />
          </el-form-item>
        </div>
        <el-button class="mobile-submit gradient" type="success" :loading="saving" :icon="Check" @click="submit">保存商品</el-button>
      </el-form>
    </section>

    <el-dialog v-model="categoryDialog" title="添加商品分类" width="92%">
      <el-input v-model="newCategory" placeholder="例如：绿植、花盆、药肥" clearable @keyup.enter="addCategory" />
      <template #footer>
        <el-button @click="categoryDialog=false">取消</el-button>
        <el-button type="success" @click="addCategory">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>
