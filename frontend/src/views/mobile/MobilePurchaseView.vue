<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ArrowLeft, Camera, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { api } from '../../api/client'

type Row = Record<string, any>

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const status = ref('')
const rows = ref<Row[]>([])
const dialogVisible = ref(false)
const receiptInput = ref<HTMLInputElement>()
const receipts = ref<Row[]>([])
const form = reactive<Row>({ items: [] })

const filteredRows = computed(() => rows.value.filter((row) => !status.value || row.status === status.value))

function itemSummary(row: Row) {
  return (row.items || []).map((item: Row) => `${item.product_name}${item.variant_name ? ` · ${item.variant_name}` : ''} × ${Number(item.quantity || 0)}${item.unit || ''}`).join('；')
}

function orderTotal(row: Row) {
  return (row.items || []).reduce((sum: number, item: Row) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0) + Number(row.freight_fee || 0) + Number(row.hll_fee || 0)
}

async function loadRows() {
  loading.value = true
  try {
    rows.value = (await api.get('/purchases/my', { params: { keyword: keyword.value.trim() } })).data.items || []
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '采购任务加载失败')
  } finally {
    loading.value = false
  }
}

function openComplete(row: Row) {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, { ...row, items: (row.items || []).map((item: Row) => ({ ...item })) })
  receipts.value = []
  dialogVisible.value = true
}

function chooseReceipt() {
  receiptInput.value?.click()
}

function handleReceipt(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (file.size > 8 * 1024 * 1024) {
    ElMessage.warning('单个收据不能超过 8MB')
    input.value = ''
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    receipts.value.push({ file_name: file.name, file_type: file.type || 'image/*', file_size: file.size, data_url: String(reader.result || ''), notes: '手机采购收据' })
    input.value = ''
  }
  reader.readAsDataURL(file)
}

async function markPurchased() {
  if ((form.items || []).some((item: Row) => Number(item.unit_price || 0) <= 0)) {
    ElMessage.warning('请填写每件货品的实际采购单价')
    return
  }
  if (!receipts.value.length) {
    ElMessage.warning('请拍照或上传采购收据')
    return
  }
  saving.value = true
  try {
    await api.post(`/purchases/${form.id}/mark-purchased`, {
      supplier: form.supplier,
      freight_fee: Number(form.freight_fee || 0),
      hll_fee: Number(form.hll_fee || 0),
      notes: form.notes || '',
      items: form.items,
      receipts: receipts.value,
    })
    ElMessage.success('采购信息已提交，等待入库')
    dialogVisible.value = false
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '采购完成提交失败')
  } finally {
    saving.value = false
  }
}

async function receive(row: Row) {
  await ElMessageBox.confirm(`确认按采购单 ${row.order_no} 入库？`, '确认入库', { type: 'warning' })
  try {
    await api.post(`/purchases/${row.id}/receive`)
    ElMessage.success('已按收据入库')
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '入库失败')
  }
}

onMounted(loadRows)
</script>

<template>
  <div class="mobile-page" v-loading="loading">
    <section class="mobile-title compact-title">
      <button type="button" @click="router.back()"><el-icon><ArrowLeft /></el-icon></button>
      <div><p>PURCHASE</p><h1>采购管理</h1></div>
      <button type="button" @click="loadRows"><el-icon><Refresh /></el-icon></button>
    </section>

    <section class="mobile-filter">
      <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="采购单、项目、供应商" @keyup.enter="loadRows" @clear="loadRows" />
      <el-segmented v-model="status" :options="[{ label: '全部', value: '' }, { label: '待采购', value: '待采购' }, { label: '待入库', value: '待入库' }]" />
    </section>

    <el-empty v-if="!filteredRows.length && !loading" description="暂无采购任务" />
    <section v-else class="mobile-task-list">
      <article v-for="row in filteredRows" :key="row.id" class="mobile-task-card">
        <div class="task-card-head"><strong>{{ row.order_no }}</strong><el-tag size="small" :type="row.status === '已入库' ? 'success' : 'warning'">{{ row.status }}</el-tag></div>
        <p>{{ row.project_name || row.source_no || '公共采购' }}</p>
        <div class="task-items">{{ itemSummary(row) || '暂无明细' }}</div>
        <p>供应商：{{ row.supplier || '待填写' }}　合计：¥{{ orderTotal(row).toFixed(2) }}</p>
        <div class="task-actions">
          <el-button v-if="!['待入库','已入库'].includes(row.status)" type="success" @click="openComplete(row)">填写采购结果</el-button>
          <el-button v-if="row.status === '待入库'" type="primary" @click="receive(row)">确认入库</el-button>
          <span v-if="row.status === '已入库'">该采购单已完成入库</span>
        </div>
      </article>
    </section>

    <el-dialog v-model="dialogVisible" title="填写采购结果" width="94%" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="供应商"><el-input v-model="form.supplier" /></el-form-item>
        <div v-for="item in form.items" :key="item.id" class="mobile-purchase-item">
          <strong>{{ item.product_name }}<span v-if="item.variant_name"> · {{ item.variant_name }}</span></strong>
          <div class="mobile-inline-two">
            <el-form-item label="数量"><el-input-number v-model="item.quantity" :min="0.01" :controls="false" /></el-form-item>
            <el-form-item label="实际单价" required><el-input-number v-model="item.unit_price" :min="0" :precision="2" :controls="false" /></el-form-item>
          </div>
        </div>
        <div class="mobile-inline-two">
          <el-form-item label="运费"><el-input-number v-model="form.freight_fee" :min="0" :controls="false" /></el-form-item>
          <el-form-item label="货拉拉费用"><el-input-number v-model="form.hll_fee" :min="0" :controls="false" /></el-form-item>
        </div>
        <el-form-item label="收据" required>
          <input ref="receiptInput" class="hidden-input" type="file" accept="image/*,.pdf" capture="environment" @change="handleReceipt" />
          <el-button type="primary" plain :icon="Camera" @click="chooseReceipt">拍照或上传收据</el-button>
          <el-tag v-for="(file, index) in receipts" :key="index" closable @close="receipts.splice(index, 1)">{{ file.file_name }}</el-tag>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.notes" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="success" :loading="saving" @click="markPurchased">提交采购结果</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.mobile-purchase-item { margin-bottom:12px; padding:12px; border-radius:8px; background:#f4f8f5; }
.mobile-purchase-item strong { display:block; margin-bottom:8px; color:#183d2b; font-size:14px; }
</style>
