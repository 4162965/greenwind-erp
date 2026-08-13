<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowDown, Check, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const loading = ref(false)
const keyword = ref('')
const includeDone = ref(false)
const orders = ref<Row[]>([])

const waitingCount = computed(() => orders.value.filter((row) => row.status === '寰呭叆搴?).length)
const doneCount = computed(() => orders.value.filter((row) => row.status === '宸插叆搴?).length)
const totalAmount = computed(() => orders.value.reduce((sum, row) => sum + orderTotal(row), 0))

function formatNumber(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') return ''
  const number = Number(value)
  if (Number.isNaN(number)) return ''
  return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
}

function orderTotal(row: Row) {
  const itemTotal = (row.items || []).reduce((sum: number, item: Row) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0)
  return itemTotal + Number(row.freight_fee || 0) + Number(row.hll_fee || 0)
}

function itemSummary(row: Row) {
  return (row.items || []).map((item: Row) => `${item.product_name}${item.variant_name ? ' / ' + item.variant_name : ''} 脳 ${formatNumber(item.quantity)}${item.unit}`).join('锛?)
}

function statusType(status: string) {
  if (status === '宸插叆搴?) return 'success'
  if (status === '寰呭叆搴?) return 'warning'
  return 'info'
}

async function loadOrders() {
  loading.value = true
  try {
    orders.value = (await api.get('/purchases/inbound', { params: { keyword: keyword.value.trim(), include_done: includeDone.value } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鍏ュ簱浠诲姟鍔犺浇澶辫触')
  } finally {
    loading.value = false
  }
}

async function receiveOrder(row: Row) {
  await ElMessageBox.confirm(
    `纭閲囪喘鍗曗€?{row.order_no}鈥濆凡缁忔竻鐐瑰苟鍏ュ簱鍚楋紵纭鍚庝細鏇存柊搴撳瓨鍜屾渶杩戦噰璐环銆俙,
    '纭鍏ュ簱',
    { type: 'warning' },
  )
  try {
    await api.post(`/purchases/${row.id}/receive`)
    ElMessage.success('鍏ュ簱瀹屾垚锛屽簱瀛樺凡鏇存柊')
    await loadOrders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鍏ュ簱澶辫触')
  }
}

loadOrders()
</script>

<template>
  <div class="page inbound-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">WAREHOUSE INBOUND</p>
        <h1>鎴戠殑鍏ュ簱浠诲姟</h1>
        <p>浠撶鏌ョ湅閲囪喘鍛樺凡瀹屾垚閲囪喘鐨勫崟鎹紝鏍稿鏁伴噺鍜屼环鏍煎悗纭鍏ュ簱锛岀郴缁熻嚜鍔ㄦ洿鏂板簱瀛樺拰鏈€杩戦噰璐环銆?/p>
      </div>
    </div>

    <div class="inventory-summary">
      <div><span>寰呭叆搴?/span><strong>{{ waitingCount }}</strong></div>
      <div><span>宸插叆搴?/span><strong>{{ doneCount }}</strong></div>
      <div><span>褰撳墠鍒楄〃閲戦</span><strong>楼{{ totalAmount.toFixed(2) }}</strong></div>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="鎼滅储閲囪喘鍗曞彿銆佷緵搴斿晢銆侀噰璐憳" @keyup.enter="loadOrders" @clear="loadOrders" />
        <el-checkbox v-model="includeDone" @change="loadOrders">鏄剧ず宸插叆搴?/el-checkbox>
        <el-button type="success" plain :icon="Search" @click="loadOrders">鏌ヨ</el-button>
        <el-button :icon="Refresh" @click="keyword=''; includeDone=false; loadOrders()">閲嶇疆</el-button>
      </div>

      <el-table v-loading="loading" :data="orders" stripe>
        <el-table-column prop="order_no" label="閲囪喘鍗曞彿" min-width="140" />
        <el-table-column prop="supplier" label="渚涘簲鍟? min-width="130" />
        <el-table-column prop="purchaser" label="閲囪喘鍛? width="110" />
        <el-table-column prop="purchase_date" label="閲囪喘鏃ユ湡" width="115" />
        <el-table-column label="閲囪喘鏄庣粏" min-width="300"><template #default="scope">{{ itemSummary(scope.row) }}</template></el-table-column>
        <el-table-column label="閲戦" width="110"><template #default="scope">楼{{ orderTotal(scope.row).toFixed(2) }}</template></el-table-column>
        <el-table-column prop="delivery_method" label="澶勭悊鏂瑰紡" width="105" />
        <el-table-column label="鐘舵€? width="95"><template #default="scope"><el-tag :type="statusType(scope.row.status)">{{ scope.row.status }}</el-tag></template></el-table-column>
        <el-table-column label="鎿嶄綔" width="95">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :disabled="scope.row.status !== '寰呭叆搴?" @click="receiveOrder(scope.row)">纭鍏ュ簱</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </article>
  </div>
</template>

