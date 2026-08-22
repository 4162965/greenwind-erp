<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ArrowDown, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const movementKeyword = ref('')
const movementType = ref('')
const rows = ref<Row[]>([])
const movements = ref<Row[]>([])
const dialogVisible = ref(false)
const allocateVisible = ref(false)
const selected = ref<Row | null>(null)
const form = reactive({ new_stock: null as number | null, notes: '' })
const allocateForm = reactive({ project_name: '', business_order_no: '', quantity: null as number | null, notes: '' })

const totalStock = computed(() => rows.value.reduce((sum, row) => sum + Number(row.stock || 0), 0))
const totalValue = computed(() => rows.value.reduce((sum, row) => sum + Number(row.stock_value || 0), 0))

function typeLabel(type: string) {
  if (type === 'bundle') return '整套'
  if (type === 'variant') return '规格'
  return '商品'
}

function typeTag(type: string) {
  if (type === 'bundle') return 'warning'
  if (type === 'variant') return 'success'
  return 'info'
}

function formatNumber(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') return ''
  const number = Number(value)
  if (Number.isNaN(number)) return ''
  return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
}

function formatMoney(value: number | string | null | undefined) {
  const number = Number(value || 0)
  if (!number) return '-'
  return `¥${formatNumber(number)}`
}

async function loadRows() {
  loading.value = true
  try {
    rows.value = (await api.get('/inventory', { params: { keyword: keyword.value.trim() } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '库存列表加载失败')
  } finally {
    loading.value = false
  }
}

async function loadMovements() {
  try {
    movements.value = (await api.get('/inventory/movements', {
      params: { keyword: movementKeyword.value.trim(), movement_type: movementType.value, limit: 80 },
    })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '库存流水加载失败')
  }
}

function openAdjust(row: Row) {
  selected.value = row
  form.new_stock = Number(row.stock || 0)
  form.notes = ''
  dialogVisible.value = true
}

function openAllocate(row: Row) {
  selected.value = row
  allocateForm.project_name = ''
  allocateForm.business_order_no = ''
  allocateForm.quantity = Number(row.stock || 0)
  allocateForm.notes = ''
  allocateVisible.value = true
}

async function saveAdjust() {
  if (!selected.value) return
  if (form.new_stock === null || Number(form.new_stock) < 0) {
    ElMessage.warning('请填写不小于 0 的库存数量')
    return
  }
  saving.value = true
  try {
    await api.post('/inventory/adjust', {
      receipt_item_id: selected.value.receipt_item_id,
      product_id: selected.value.product_id,
      variant_id: selected.value.variant_id,
      new_stock: Number(form.new_stock),
      notes: form.notes,
    })
    ElMessage.success('库存已调整')
    dialogVisible.value = false
    await loadRows()
    await loadMovements()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '库存调整失败')
  } finally {
    saving.value = false
  }
}

async function saveAllocate() {
  if (!selected.value?.receipt_item_id) return
  if (!allocateForm.project_name.trim() && !allocateForm.business_order_no.trim()) {
    ElMessage.warning('请填写项目或订单去向')
    return
  }
  if (!allocateForm.quantity || Number(allocateForm.quantity) <= 0) {
    ElMessage.warning('请填写大于 0 的分配数量')
    return
  }
  if (Number(allocateForm.quantity) > Number(selected.value.stock || 0)) {
    ElMessage.warning('分配数量不能超过未安排余量')
    return
  }
  saving.value = true
  try {
    await api.post(`/inventory/receipt-items/${selected.value.receipt_item_id}/allocate`, {
      project_name: allocateForm.project_name,
      business_order_no: allocateForm.business_order_no,
      quantity: Number(allocateForm.quantity),
      notes: allocateForm.notes,
    })
    ElMessage.success('收据余量已分配')
    allocateVisible.value = false
    await loadRows()
    await loadMovements()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '收据余量分配失败')
  } finally {
    saving.value = false
  }
}

loadRows()
loadMovements()
</script>

<template>
  <div class="page inventory-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">INVENTORY</p>
        <h1>未安排库存</h1>
        <p>按收据余量查看暂未安排去向的商品，仓管可以盘点调整数量并记录原因。</p>
      </div>
    </div>

    <div class="inventory-summary">
      <div><span>库存条目</span><strong>{{ rows.length }}</strong></div>
      <div><span>当前数量合计</span><strong>{{ formatNumber(totalStock) }}</strong></div>
      <div><span>未安排库存金额</span><strong>{{ formatMoney(totalValue) }}</strong></div>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar inventory-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="搜索规格编码、商品编码、商品名称或分类" @keyup.enter="loadRows" @clear="loadRows" />
        <el-button type="success" plain :icon="Search" @click="loadRows">查询</el-button>
        <el-button :icon="Refresh" @click="keyword=''; loadRows()">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="receipt_no" label="收据号" min-width="150" />
        <el-table-column prop="receipt_date" label="收据日期" width="112" />
        <el-table-column prop="supplier" label="供应商" min-width="130" show-overflow-tooltip />
        <el-table-column prop="variant_code" label="规格编码" min-width="150">
          <template #default="scope">{{ scope.row.variant_code || '—' }}</template>
        </el-table-column>
        <el-table-column prop="product_code" label="商品编码" min-width="130" />
        <el-table-column prop="product_name" label="商品名称" min-width="180" />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column label="类型" width="86">
          <template #default="scope"><el-tag :type="typeTag(scope.row.item_type)" size="small">{{ typeLabel(scope.row.item_type) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="specification" label="规格/型号" min-width="160" show-overflow-tooltip />
        <el-table-column label="库存" width="105">
          <template #default="scope"><strong :class="{ danger: Number(scope.row.stock || 0) <= 0 }">{{ formatNumber(scope.row.stock) }}</strong></template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column label="最近采购价" width="115">
          <template #default="scope">{{ formatMoney(scope.row.reference_purchase_price) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="scope"><el-tag :type="scope.row.status === '启用' ? 'success' : 'info'" size="small">{{ scope.row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="95">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">更多<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :icon="Plus" @click="openAllocate(scope.row)">分配去向</el-dropdown-item>
                  <el-dropdown-item :icon="Edit" @click="openAdjust(scope.row)">盘点调整</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <article class="panel table-panel movement-panel">
      <div class="panel-head movement-head">
        <div>
          <h3>最近库存流水</h3>
          <p>记录收据余量盘点、损耗、退回等库存变化，后续会继续接项目出库和成本报表。</p>
        </div>
      </div>
      <div class="table-toolbar inventory-toolbar">
        <el-input v-model="movementKeyword" clearable :prefix-icon="Search" placeholder="搜索商品、来源单号、操作人" @keyup.enter="loadMovements" @clear="loadMovements" />
        <el-select v-model="movementType" clearable placeholder="流水类型" @change="loadMovements">
          <el-option label="采购入库" value="采购入库" />
          <el-option label="盘点调整" value="盘点调整" />
          <el-option label="收据余量分配" value="收据余量分配" />
        </el-select>
        <el-button type="success" plain :icon="Search" @click="loadMovements">查询流水</el-button>
        <el-button :icon="Refresh" @click="movementKeyword=''; movementType=''; loadMovements()">重置</el-button>
      </div>
      <el-table :data="movements" stripe>
        <el-table-column prop="created_at" label="时间" min-width="155">
          <template #default="scope">{{ scope.row.created_at ? scope.row.created_at.replace('T', ' ').slice(0, 19) : '' }}</template>
        </el-table-column>
        <el-table-column prop="movement_type" label="类型" width="105" />
        <el-table-column prop="direction" label="方向" width="76">
          <template #default="scope"><el-tag :type="scope.row.direction === '入库' ? 'success' : 'warning'" size="small">{{ scope.row.direction }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="product_name" label="商品" min-width="160" />
        <el-table-column prop="variant_name" label="规格" min-width="130" show-overflow-tooltip />
        <el-table-column label="数量" width="95">
          <template #default="scope">{{ formatNumber(scope.row.quantity) }} {{ scope.row.unit }}</template>
        </el-table-column>
        <el-table-column label="库存变化" min-width="130">
          <template #default="scope">{{ formatNumber(scope.row.before_stock) }} → {{ formatNumber(scope.row.after_stock) }}</template>
        </el-table-column>
        <el-table-column label="金额" width="100">
          <template #default="scope">{{ formatMoney(scope.row.total_amount) }}</template>
        </el-table-column>
        <el-table-column label="来源" min-width="150">
          <template #default="scope">{{ [scope.row.source_type, scope.row.source_no].filter(Boolean).join('，') || '-' }}</template>
        </el-table-column>
        <el-table-column prop="operator" label="操作人" width="100" />
        <el-table-column prop="notes" label="备注" min-width="150" show-overflow-tooltip />
      </el-table>
    </article>

    <el-dialog v-model="dialogVisible" title="盘点调整" width="520px" destroy-on-close>
      <div v-if="selected" class="adjust-card">
        <div><span>规格编码</span><strong>{{ selected.variant_code || '—' }}</strong></div>
        <div><span>商品</span><strong>{{ selected.product_name }}</strong></div>
        <div><span>规格</span><strong>{{ selected.specification }}</strong></div>
        <div><span>当前库存</span><strong>{{ formatNumber(selected.stock) }} {{ selected.unit }}</strong></div>
      </div>
      <el-form label-position="top">
        <el-form-item label="盘点后数量" required>
          <el-input-number v-model="form.new_stock" :min="0" :controls="false" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="3" placeholder="例如：仓库盘点、破损报损、历史数据修正" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="success" :loading="saving" @click="saveAdjust">保存调整</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="allocateVisible" title="分配收据余量" width="560px" destroy-on-close>
      <div v-if="selected" class="adjust-card">
        <div><span>收据号</span><strong>{{ selected.receipt_no || '-' }}</strong></div>
        <div><span>商品</span><strong>{{ selected.product_name }}</strong></div>
        <div><span>规格</span><strong>{{ selected.specification }}</strong></div>
        <div><span>未安排</span><strong>{{ formatNumber(selected.stock) }} {{ selected.unit }}</strong></div>
        <div><span>单价</span><strong>{{ formatMoney(selected.reference_purchase_price) }}</strong></div>
      </div>
      <el-form label-position="top">
        <el-form-item label="去向项目">
          <el-input v-model="allocateForm.project_name" placeholder="例如：租摆A项目 / 工程B项目" />
        </el-form-item>
        <el-form-item label="订单号">
          <el-input v-model="allocateForm.business_order_no" placeholder="可填订单号，系统会优先按订单匹配项目" />
        </el-form-item>
        <el-form-item label="分配数量" required>
          <el-input-number v-model="allocateForm.quantity" :min="0" :max="Number(selected?.stock || 0)" :precision="2" :controls="false" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="allocateForm.notes" type="textarea" :rows="3" placeholder="例如：补给某订单、临时项目领用、客户指定" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="allocateVisible=false">取消</el-button>
        <el-button type="success" :loading="saving" @click="saveAllocate">确认分配</el-button>
      </template>
    </el-dialog>
  </div>
</template>
