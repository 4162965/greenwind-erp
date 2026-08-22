<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Refresh, Search } from '@element-plus/icons-vue'
import { api } from '../api/client'

type Row = Record<string, any>

const route = useRoute()
const loading = ref(false)
const rows = ref<Row[]>([])
const detailRows = ref<Row[]>([])
const summary = ref<Row>({})
const typeStats = ref<Row[]>([])
const statusStats = ref<Row[]>([])
const categories = ref<string[]>([])
const filters = reactive({ keyword: '', category: '', start_date: '', end_date: '' })

const reportType = computed(() => String(route.params.reportType || 'orders'))
const isGoods = computed(() => reportType.value === 'goods')
const isProfit = computed(() => reportType.value === 'profit')
const pageTitle = computed(() => isGoods.value ? '商品汇总' : isProfit.value ? '销售利润' : '订单销量')
const pageDesc = computed(() => isGoods.value ? '按商品和规格汇总库存、采购成本和销售金额。' : isProfit.value ? '先用项目成本中心的数据查看收入、成本、利润。' : '按订单类型、状态和日期统计业务量。')

function money(value: unknown) {
  return `¥${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`
}

function numberText(value: unknown) {
  return Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })
}

async function loadRows() {
  loading.value = true
  try {
    if (isGoods.value) {
      const response = await api.get('/reports/goods-summary', { params: { keyword: filters.keyword.trim(), category: filters.category || undefined } })
      rows.value = response.data.items || []
      detailRows.value = []
      summary.value = response.data.summary || {}
      categories.value = response.data.categories || []
      typeStats.value = []
      statusStats.value = []
      return
    }
    if (isProfit.value) {
      const response = await api.get('/reports/project-costs', { params: { keyword: filters.keyword.trim(), start_date: filters.start_date || undefined, end_date: filters.end_date || undefined } })
      rows.value = response.data.items || []
      detailRows.value = response.data.details || []
      summary.value = response.data.summary || {}
      typeStats.value = []
      statusStats.value = []
      return
    }
    const response = await api.get('/reports/order-stats', { params: { keyword: filters.keyword.trim(), start_date: filters.start_date || undefined, end_date: filters.end_date || undefined } })
    rows.value = response.data.items || []
    detailRows.value = []
    summary.value = response.data.summary || {}
    typeStats.value = response.data.type_stats || []
    statusStats.value = response.data.status_stats || []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.keyword = ''
  filters.category = ''
  filters.start_date = ''
  filters.end_date = ''
  loadRows()
}

watch(() => route.params.reportType, loadRows)
onMounted(loadRows)
</script>

<template>
  <div class="page report-summary-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">REPORT</p>
        <h1>{{ pageTitle }}</h1>
        <p>{{ pageDesc }}</p>
      </div>
    </div>

    <div v-if="isGoods" class="inventory-summary report-summary-cards">
      <div><span>商品数量</span><strong>{{ numberText(summary.product_count) }}</strong></div>
      <div><span>规格数量</span><strong>{{ numberText(summary.variant_count) }}</strong></div>
      <div><span>采购库存金额</span><strong>{{ money(summary.stock_value) }}</strong></div>
      <div><span>销售库存金额</span><strong>{{ money(summary.sale_value) }}</strong></div>
    </div>
    <div v-else-if="isProfit" class="inventory-summary cost-summary">
      <div><span>合同折算收入</span><strong>{{ money(summary.customer_income) }}</strong></div>
      <div><span>总成本</span><strong>{{ money(summary.total_cost) }}</strong></div>
      <div><span>利润</span><strong :class="{ danger: Number(summary.profit || 0) < 0 }">{{ money(summary.profit) }}</strong></div>
      <div><span>利润率</span><strong>{{ numberText(summary.profit_rate) }}%</strong></div>
      <div><span>已收款</span><strong>{{ money(summary.receipt_amount) }}</strong></div>
    </div>
    <div v-else class="inventory-summary report-summary-cards">
      <div><span>订单数量</span><strong>{{ numberText(summary.order_count) }}</strong></div>
      <div><span>明细数量</span><strong>{{ numberText(summary.item_count) }}</strong></div>
      <div><span>订单金额</span><strong>{{ money(summary.amount) }}</strong></div>
      <div><span>未完成订单</span><strong>{{ numberText(summary.pending_count) }}</strong></div>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar report-toolbar">
        <el-input v-model="filters.keyword" clearable :prefix-icon="Search" placeholder="搜索编号、项目、客户、商品" @keyup.enter="loadRows" @clear="loadRows" />
        <el-select v-if="isGoods" v-model="filters.category" clearable placeholder="商品分类" @change="loadRows">
          <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
        </el-select>
        <template v-else>
          <el-date-picker v-model="filters.start_date" value-format="YYYY-MM-DD" placeholder="开始日期" />
          <el-date-picker v-model="filters.end_date" value-format="YYYY-MM-DD" placeholder="结束日期" />
        </template>
        <el-button type="success" plain :icon="Search" @click="loadRows">查询</el-button>
        <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
      </div>

      <div v-if="!isGoods && !isProfit" class="report-split">
        <div>
          <h3>按订单类型</h3>
          <div class="composition-list">
            <div v-for="item in typeStats" :key="item.order_type">
              <span>{{ item.order_type }}</span>
              <el-progress :percentage="summary.order_count ? Math.round(Number(item.count || 0) / Number(summary.order_count || 1) * 100) : 0" :stroke-width="9" color="#16834b" />
              <strong>{{ item.count }}单</strong>
            </div>
          </div>
        </div>
        <div>
          <h3>按状态</h3>
          <div class="status-chips"><el-tag v-for="item in statusStats" :key="item.status" effect="light">{{ item.status }} {{ item.count }}</el-tag></div>
        </div>
      </div>

      <el-table v-loading="loading" :data="rows" stripe>
        <template v-if="isGoods">
          <el-table-column prop="code" label="商品编号" width="130" fixed />
          <el-table-column prop="name" label="商品名称" min-width="170" />
          <el-table-column prop="category" label="分类" width="90" />
          <el-table-column prop="specification" label="规格" min-width="220" show-overflow-tooltip />
          <el-table-column prop="variant_count" label="规格数" width="80" />
          <el-table-column label="库存" width="100"><template #default="scope">{{ numberText(scope.row.stock) }} {{ scope.row.unit }}</template></el-table-column>
          <el-table-column label="采购均价" width="110"><template #default="scope">{{ money(scope.row.purchase_price) }}</template></el-table-column>
          <el-table-column label="销售均价" width="110"><template #default="scope">{{ money(scope.row.sale_price) }}</template></el-table-column>
          <el-table-column label="采购库存金额" width="130"><template #default="scope">{{ money(scope.row.stock_value) }}</template></el-table-column>
          <el-table-column label="销售库存金额" width="130"><template #default="scope">{{ money(scope.row.sale_value) }}</template></el-table-column>
          <el-table-column label="成套采购" width="95"><template #default="scope"><el-tag v-if="scope.row.package_conversion_enabled" type="warning">是</el-tag><span v-else>否</span></template></el-table-column>
        </template>
        <template v-else-if="isProfit">
          <el-table-column prop="project_name" label="项目" min-width="190" fixed />
          <el-table-column label="收入" width="120"><template #default="scope">{{ money(scope.row.customer_income) }}</template></el-table-column>
          <el-table-column label="采购成本" width="120"><template #default="scope">{{ money(scope.row.purchase_cost) }}</template></el-table-column>
          <el-table-column label="出库成本" width="120"><template #default="scope">{{ money(scope.row.stock_out_cost) }}</template></el-table-column>
          <el-table-column label="工资" width="120"><template #default="scope">{{ money(scope.row.salary_cost) }}</template></el-table-column>
          <el-table-column label="其他/物流" width="130"><template #default="scope">{{ money(Number(scope.row.other_cost || 0) + Number(scope.row.logistics_cost || 0)) }}</template></el-table-column>
          <el-table-column label="利润" width="120"><template #default="scope"><strong :class="{ danger: Number(scope.row.profit || 0) < 0 }">{{ money(scope.row.profit) }}</strong></template></el-table-column>
          <el-table-column label="利润率" width="100"><template #default="scope">{{ numberText(scope.row.profit_rate) }}%</template></el-table-column>
          <el-table-column label="已收款" width="120"><template #default="scope">{{ money(scope.row.receipt_amount) }}</template></el-table-column>
        </template>
        <template v-else>
          <el-table-column prop="order_no" label="订单编号" width="145" fixed />
          <el-table-column prop="order_type" label="类型" width="105" />
          <el-table-column prop="project_name" label="项目" min-width="170" show-overflow-tooltip />
          <el-table-column prop="customer_name" label="客户" min-width="130" show-overflow-tooltip />
          <el-table-column prop="requester" label="下单人" width="95" />
          <el-table-column prop="order_date" label="下单日期" width="110" />
          <el-table-column prop="item_count" label="明细" width="70" />
          <el-table-column label="数量" width="90"><template #default="scope">{{ numberText(scope.row.quantity) }}</template></el-table-column>
          <el-table-column label="金额" width="110"><template #default="scope">{{ money(scope.row.amount) }}</template></el-table-column>
          <el-table-column prop="status" label="状态" width="95" />
        </template>
      </el-table>

      <div v-if="isProfit" class="cost-detail-block">
        <h3>项目成本明细</h3>
        <el-table :data="detailRows" stripe size="small">
          <el-table-column prop="date" label="日期" width="110" />
          <el-table-column prop="project_name" label="项目" min-width="170" show-overflow-tooltip />
          <el-table-column prop="category" label="分类" width="120" />
          <el-table-column prop="source_no" label="来源单号" min-width="130" />
          <el-table-column prop="description" label="说明" min-width="260" show-overflow-tooltip />
          <el-table-column label="收入" width="110"><template #default="scope">{{ money(scope.row.income) }}</template></el-table-column>
          <el-table-column label="成本" width="110"><template #default="scope">{{ money(scope.row.cost) }}</template></el-table-column>
        </el-table>
      </div>
    </article>
  </div>
</template>
