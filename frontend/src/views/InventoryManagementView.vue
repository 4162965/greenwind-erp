<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ArrowDown, Edit, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const lowStockOnly = ref(false)
const movementKeyword = ref('')
const movementType = ref('')
const rows = ref<Row[]>([])
const movements = ref<Row[]>([])
const dialogVisible = ref(false)
const selected = ref<Row | null>(null)
const form = reactive({ new_stock: null as number | null, notes: '' })

const totalStock = computed(() => rows.value.reduce((sum, row) => sum + Number(row.stock || 0), 0))
const noStockCount = computed(() => rows.value.filter((row) => Number(row.stock || 0) <= 0).length)

function typeLabel(type: string) {
  if (type === 'bundle') return '鏁村'
  if (type === 'variant') return '瑙勬牸'
  return '鍟嗗搧'
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
  if (!number) return '鈥?
  return `楼${formatNumber(number)}`
}

async function loadRows() {
  loading.value = true
  try {
    rows.value = (await api.get('/inventory', { params: { keyword: keyword.value.trim(), low_stock_only: lowStockOnly.value } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '搴撳瓨鍒楄〃鍔犺浇澶辫触')
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
    ElMessage.error(error.response?.data?.detail || '搴撳瓨娴佹按鍔犺浇澶辫触')
  }
}

function openAdjust(row: Row) {
  selected.value = row
  form.new_stock = Number(row.stock || 0)
  form.notes = ''
  dialogVisible.value = true
}

async function saveAdjust() {
  if (!selected.value) return
  if (form.new_stock === null || Number(form.new_stock) < 0) {
    ElMessage.warning('璇峰～鍐欎笉灏忎簬 0 鐨勫簱瀛樻暟閲?)
    return
  }
  saving.value = true
  try {
    await api.post('/inventory/adjust', {
      product_id: selected.value.product_id,
      variant_id: selected.value.variant_id,
      new_stock: Number(form.new_stock),
      notes: form.notes,
    })
    ElMessage.success('搴撳瓨宸茶皟鏁?)
    dialogVisible.value = false
    await loadRows()
    await loadMovements()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '搴撳瓨璋冩暣澶辫触')
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
        <h1>搴撳瓨鐩樼偣</h1>
        <p>鎸夊晢鍝併€佽鏍笺€佹垚濂楅噰璐垎鍒煡鐪嬪簱瀛橈紱浠撶鍙互鍏堝仛鎵嬪伐鐩樼偣璋冩暣銆?/p>
      </div>
    </div>

    <div class="inventory-summary">
      <div><span>搴撳瓨鏉＄洰</span><strong>{{ rows.length }}</strong></div>
      <div><span>褰撳墠鏁伴噺鍚堣</span><strong>{{ formatNumber(totalStock) }}</strong></div>
      <div><span>缂鸿揣/闆跺簱瀛?/span><strong>{{ noStockCount }}</strong></div>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar inventory-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="搜索规格编码、商品编码、商品名称或分类" @keyup.enter="loadRows" @clear="loadRows" />
        <el-checkbox v-model="lowStockOnly" @change="loadRows">鍙湅缂鸿揣</el-checkbox>
        <el-button type="success" plain :icon="Search" @click="loadRows">鏌ヨ</el-button>
        <el-button :icon="Refresh" @click="keyword=''; lowStockOnly=false; loadRows()">閲嶇疆</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="variant_code" label="规格编码" min-width="150">
          <template #default="scope">{{ scope.row.variant_code || '—' }}</template>
        </el-table-column>
        <el-table-column prop="product_code" label="商品编码" min-width="130" />
        <el-table-column prop="product_name" label="鍟嗗搧鍚嶇О" min-width="180" />
        <el-table-column prop="category" label="鍒嗙被" width="100" />
        <el-table-column label="绫诲瀷" width="86">
          <template #default="scope"><el-tag :type="typeTag(scope.row.item_type)" size="small">{{ typeLabel(scope.row.item_type) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="specification" label="瑙勬牸/鍨嬪彿" min-width="160" show-overflow-tooltip />
        <el-table-column label="搴撳瓨" width="105">
          <template #default="scope"><strong :class="{ danger: Number(scope.row.stock || 0) <= 0 }">{{ formatNumber(scope.row.stock) }}</strong></template>
        </el-table-column>
        <el-table-column prop="unit" label="鍗曚綅" width="80" />
        <el-table-column label="鏈€杩戦噰璐环" width="115">
          <template #default="scope">{{ formatMoney(scope.row.reference_purchase_price) }}</template>
        </el-table-column>
        <el-table-column label="鐘舵€? width="90">
          <template #default="scope"><el-tag :type="scope.row.status === '鍚敤' ? 'success' : 'info'" size="small">{{ scope.row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column label="鎿嶄綔" width="95">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :icon="Edit" @click="openAdjust(scope.row)">鐩樼偣璋冩暣</el-dropdown-item>
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
          <h3>鏈€杩戝簱瀛樻祦姘?/h3>
          <p>璁板綍閲囪喘鍏ュ簱銆佺洏鐐硅皟鏁寸瓑搴撳瓨鍙樺寲锛屽悗闈細缁х画鎺ラ」鐩嚭搴撱€佹挙鑺便€佹姤鎹熴€?/p>
        </div>
      </div>
      <div class="table-toolbar inventory-toolbar">
        <el-input v-model="movementKeyword" clearable :prefix-icon="Search" placeholder="鎼滅储鍟嗗搧銆佹潵婧愬崟鍙枫€佹搷浣滀汉" @keyup.enter="loadMovements" @clear="loadMovements" />
        <el-select v-model="movementType" clearable placeholder="娴佹按绫诲瀷" @change="loadMovements">
          <el-option label="閲囪喘鍏ュ簱" value="閲囪喘鍏ュ簱" />
          <el-option label="鐩樼偣璋冩暣" value="鐩樼偣璋冩暣" />
        </el-select>
        <el-button type="success" plain :icon="Search" @click="loadMovements">鏌ヨ娴佹按</el-button>
        <el-button :icon="Refresh" @click="movementKeyword=''; movementType=''; loadMovements()">閲嶇疆</el-button>
      </div>
      <el-table :data="movements" stripe>
        <el-table-column prop="created_at" label="鏃堕棿" min-width="155">
          <template #default="scope">{{ scope.row.created_at ? scope.row.created_at.replace('T', ' ').slice(0, 19) : '' }}</template>
        </el-table-column>
        <el-table-column prop="movement_type" label="绫诲瀷" width="95" />
        <el-table-column prop="direction" label="鏂瑰悜" width="76">
          <template #default="scope"><el-tag :type="scope.row.direction === '鍏ュ簱' ? 'success' : 'warning'" size="small">{{ scope.row.direction }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="product_name" label="鍟嗗搧" min-width="160" />
        <el-table-column prop="variant_name" label="瑙勬牸" min-width="130" show-overflow-tooltip />
        <el-table-column label="鏁伴噺" width="95">
          <template #default="scope">{{ formatNumber(scope.row.quantity) }} {{ scope.row.unit }}</template>
        </el-table-column>
        <el-table-column label="搴撳瓨鍙樺寲" min-width="130">
          <template #default="scope">{{ formatNumber(scope.row.before_stock) }} 鈫?{{ formatNumber(scope.row.after_stock) }}</template>
        </el-table-column>
        <el-table-column label="閲戦" width="100">
          <template #default="scope">{{ formatMoney(scope.row.total_amount) }}</template>
        </el-table-column>
        <el-table-column label="鏉ユ簮" min-width="150">
          <template #default="scope">{{ [scope.row.source_type, scope.row.source_no].filter(Boolean).join('锛?) || '鈥? }}</template>
        </el-table-column>
        <el-table-column prop="operator" label="鎿嶄綔浜? width="100" />
        <el-table-column prop="notes" label="澶囨敞" min-width="150" show-overflow-tooltip />
      </el-table>
    </article>

    <el-dialog v-model="dialogVisible" title="鐩樼偣璋冩暣" width="520px" destroy-on-close>
      <div v-if="selected" class="adjust-card">
        <div><span>规格编码</span><strong>{{ selected.variant_code || '—' }}</strong></div>
        <div><span>商品</span><strong>{{ selected.product_name }}</strong></div>
        <div><span>规格</span><strong>{{ selected.specification }}</strong></div>
        <div><span>褰撳墠搴撳瓨</span><strong>{{ formatNumber(selected.stock) }} {{ selected.unit }}</strong></div>
      </div>
      <el-form label-position="top">
        <el-form-item label="鐩樼偣鍚庡簱瀛? required>
          <el-input-number v-model="form.new_stock" :min="0" :controls="false" style="width:100%" />
        </el-form-item>
        <el-form-item label="澶囨敞">
          <el-input v-model="form.notes" type="textarea" :rows="3" placeholder="渚嬪锛氫粨搴撶洏鐐广€佺牬鎹熸姤鎹熴€佸巻鍙叉暟鎹慨姝? />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">鍙栨秷</el-button>
        <el-button type="success" :loading="saving" @click="saveAdjust">淇濆瓨璋冩暣</el-button>
      </template>
    </el-dialog>
  </div>
</template>

