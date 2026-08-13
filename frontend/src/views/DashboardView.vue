<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Calendar, Check, Coin, Goods, Refresh, Warning } from '@element-plus/icons-vue'
import type { Component } from 'vue'
import { api } from '../api/client'

const data = ref<any>({ metrics: [], sales: [], labels: [], todos: [], composition: [], finance: {}, contract_alerts: [], vehicle_alerts: [], schedules: [] })
const loading = ref(false)
const icons: Record<number, Component> = { 0: Goods, 1: Check, 2: Warning, 3: Coin }
const colors: Record<number, string> = { 0: 'green', 1: 'blue', 2: 'amber', 3: 'violet' }
const metricIcon = (index: unknown) => icons[Number(index)] || Check
const metricColor = (index: unknown) => colors[Number(index)] || 'green'
const todayText = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })

function money(value: unknown) {
  return `¥${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`
}

async function loadData() {
  loading.value = true
  try {
    data.value = (await api.get('/dashboard/summary')).data
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

const chartPoints = computed(() => {
  const values: number[] = data.value.sales || []
  if (!values.length) return ''
  const max = Math.max(...values, 1)
  return values.map((value, index) => `${20 + index * 73},${220 - (value / max) * 175}`).join(' ')
})

const compositionRows = computed(() => {
  const total = Number(data.value.total_orders || 0)
  return (data.value.composition || []).filter((item: any) => Number(item.value || 0) > 0).map((item: any) => ({
    ...item,
    percent: total ? Math.round(Number(item.value || 0) / total * 100) : 0,
  }))
})

const operationRate = computed(() => {
  const todoCount = Number(data.value.todos?.length || 0)
  const scheduleCount = Number(data.value.schedules?.length || 0)
  const doneBase = Math.max(scheduleCount + todoCount, 1)
  return Math.max(58, Math.min(96, Math.round((scheduleCount / doneBase) * 100) || 72))
})

const collectionRate = computed(() => {
  const total = Number(data.value.finance?.receivable_total || 0)
  const received = Number(data.value.finance?.received_total || 0)
  return total ? Math.min(100, Math.round(received / total * 100)) : 68
})

const taskPressureRate = computed(() => {
  const todos = Number(data.value.todos?.length || 0)
  const alerts = Number(data.value.contract_alerts?.length || 0) + Number(data.value.vehicle_alerts?.length || 0)
  return Math.min(96, Math.max(36, (todos * 18) + (alerts * 12)))
})

const activeOrderRate = computed(() => {
  const orders = Number(data.value.total_orders || 0)
  return Math.min(96, Math.max(45, 48 + orders * 4))
})

const sparkBars = computed(() => {
  const values: number[] = data.value.sales || []
  const max = Math.max(...values, 1)
  return values.map((value) => Math.max(18, Math.round(Number(value || 0) / max * 76)))
})
</script>

<template>
  <div v-loading="loading" class="page dashboard">
    <div class="page-heading">
      <div>
        <p class="eyebrow">工作台</p>
        <h1>工作台</h1>
        <p>这里显示真实业务待办：采购、配送、审批、合同、应收和车辆提醒。</p>
      </div>
      <el-button :icon="Refresh" @click="loadData">{{ todayText }}</el-button>
    </div>

    <div class="dashboard-hero-row">
      <section class="welcome-card">
        <div>
          <span>绿风环境花卉 ERP</span>
          <h2>早上好，欢迎回来</h2>
          <p>租摆、换花、采购、配送、回款这些今天要盯的事，都放到一个运营首页里。</p>
          <div class="hero-actions">
            <router-link to="/module/order/lease">新建租摆单</router-link>
            <router-link to="/module/schedule/list">查看安排表</router-link>
          </div>
        </div>
        <div class="welcome-illustration">
          <div class="plant-pot"></div>
          <div class="plant-leaf leaf-a"></div>
          <div class="plant-leaf leaf-b"></div>
          <div class="plant-leaf leaf-c"></div>
        </div>
      </section>
      <section class="mini-panel">
        <div class="mini-panel-head"><strong>今日运营进度</strong><span>实时业务</span></div>
        <div class="mini-progress-wrap">
          <div class="mini-progress-ring" :style="{ '--rate': `${operationRate}%` }">
            <strong>{{ operationRate }}%</strong>
            <span>计划完成度</span>
          </div>
          <div class="mini-list">
            <div><span>待办事项</span><strong>{{ data.todos?.length || 0 }}</strong></div>
            <div><span>今日/明日安排</span><strong>{{ data.schedules?.length || 0 }}</strong></div>
            <div><span>车辆提醒</span><strong>{{ data.vehicle_alerts?.length || 0 }}</strong></div>
          </div>
        </div>
      </section>
    </div>

    <div class="color-module-grid">
      <router-link class="color-module module-blue" to="/module/order/lease">
        <span>订单中心</span><strong>租摆 / 销售 / 换花</strong><small>新建与跟进订单</small><i></i>
      </router-link>
      <router-link class="color-module module-purple" to="/projects">
        <span>项目档案</span><strong>客户项目与位置</strong><small>楼层、区域、植物清单</small><i></i>
      </router-link>
      <router-link class="color-module module-orange" to="/module/purchase/list">
        <span>采购库存</span><strong>采购 / 入库 / 出库</strong><small>供应、仓库和成本</small><i></i>
      </router-link>
      <router-link class="color-module module-mint" to="/module/finance/receivable">
        <span>财务回款</span><strong>应收 / 开票 / 收款</strong><small>合同账期与未收款</small><i></i>
      </router-link>
    </div>

    <div class="notice-card-grid">
      <router-link class="notice-card notice-a" to="/module/workflow/approval">
        <b>审批中心</b>
        <span>换花成本、项目采购审核</span>
        <small>查看待审核事项 →</small>
      </router-link>
      <router-link class="notice-card notice-b" to="/module/purchase/my">
        <b>我的采购</b>
        <span>采购员填写实际价格并入库</span>
        <small>进入采购处理 →</small>
      </router-link>
      <router-link class="notice-card notice-c" to="/module/schedule/list">
        <b>每日安排</b>
        <span>司机、跟车、养护员查看派工</span>
        <small>查看每日安排 →</small>
      </router-link>
      <router-link class="notice-card notice-d" to="/module/report/project-cost">
        <b>项目费用</b>
        <span>日、周、月、年成本收入汇总</span>
        <small>查看项目成本 →</small>
      </router-link>
    </div>

    <div class="metric-grid">
      <article v-for="(metric, index) in data.metrics" :key="metric.label" class="metric-card">
        <div class="metric-icon" :class="metricColor(index)"><el-icon><component :is="metricIcon(index)" /></el-icon></div>
        <div>
          <span>{{ metric.label }}</span>
          <strong>{{ metric.currency ? money(metric.value) : metric.value }}</strong>
          <small>{{ metric.trend }}</small>
        </div>
      </article>
    </div>

    <div class="dashboard-insight-row">
      <article class="insight-gauge-card gauge-receivable">
        <div class="panel-head"><div><h3>回款仪表</h3><p>应收与已收综合进度</p></div><router-link to="/module/finance/receivable">去处理</router-link></div>
        <div class="gauge-body">
          <div class="gauge-ring big" :style="{ '--rate': `${collectionRate}%` }">
            <strong>{{ collectionRate }}%</strong>
            <span>回款率</span>
          </div>
          <div class="gauge-side">
            <div><span>应收总额</span><b>{{ money(data.finance?.receivable_total) }}</b></div>
            <div><span>未收款</span><b class="danger">{{ money(data.finance?.unreceived_total) }}</b></div>
          </div>
        </div>
      </article>

      <article class="insight-gauge-card gauge-task">
        <div class="panel-head"><div><h3>任务压力</h3><p>待办、合同、车辆提醒</p></div><router-link to="/module/workflow/progress">看进度</router-link></div>
        <div class="gauge-body">
          <div class="gauge-ring amber" :style="{ '--rate': `${taskPressureRate}%` }">
            <strong>{{ taskPressureRate }}%</strong>
            <span>压力值</span>
          </div>
          <div class="bubble-list">
            <span>待办 {{ data.todos?.length || 0 }}</span>
            <span>合同 {{ data.contract_alerts?.length || 0 }}</span>
            <span>车辆 {{ data.vehicle_alerts?.length || 0 }}</span>
          </div>
        </div>
      </article>

      <article class="insight-trend-card">
        <div class="panel-head"><div><h3>订单活跃度</h3><p>近 7 天新增走势</p></div><b>{{ activeOrderRate }}%</b></div>
        <div class="spark-bar-chart">
          <i v-for="(height, index) in sparkBars" :key="index" :style="{ height: `${height}%` }"></i>
        </div>
        <div class="spark-labels"><span v-for="label in data.labels" :key="label">{{ label }}</span></div>
      </article>
    </div>

    <div class="dashboard-grid">
      <article class="panel sales-panel">
        <div class="panel-head"><div><h3>近 7 天订单</h3><p>按订单日期统计新增订单</p></div><el-tag type="success" effect="light">本月 {{ data.finance?.month_orders || 0 }} 单</el-tag></div>
        <div class="native-chart">
          <svg viewBox="0 0 480 250" preserveAspectRatio="none">
            <defs><linearGradient id="salesFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16834b" stop-opacity=".25"/><stop offset="1" stop-color="#16834b" stop-opacity="0"/></linearGradient></defs>
            <g class="grid-lines"><line v-for="y in [45,90,135,180,220]" :key="y" x1="20" :y1="y" x2="460" :y2="y" /></g>
            <polygon v-if="chartPoints" :points="`20,220 ${chartPoints} 458,220`" fill="url(#salesFill)"/>
            <polyline :points="chartPoints" fill="none" stroke="#16834b" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <div class="chart-labels"><span v-for="label in data.labels" :key="label">{{ label }}</span></div>
        </div>
      </article>

      <article class="panel finance-overview">
        <div class="panel-head"><div><h3>财务摘要</h3><p>应收、已收、未收款快速查看</p></div><router-link to="/module/finance/receivable">查看应收</router-link></div>
        <div class="finance-cards">
          <div><span>应收总额</span><strong>{{ money(data.finance?.receivable_total) }}</strong></div>
          <div><span>已收款</span><strong>{{ money(data.finance?.received_total) }}</strong></div>
          <div><span>未收款</span><strong class="danger">{{ money(data.finance?.unreceived_total) }}</strong></div>
          <div><span>本月回款</span><strong>{{ money(data.finance?.month_receipts) }}</strong></div>
        </div>
      </article>

      <article class="panel todo-panel">
        <div class="panel-head"><div><h3>待办事项</h3><p>需要尽快处理的业务</p></div></div>
        <div class="todo-list">
          <router-link v-for="todo in data.todos" :key="`${todo.type}-${todo.title}`" class="todo-item" :to="todo.path || '/'">
            <span class="todo-check"></span>
            <div><strong>{{ todo.title }}</strong><small>{{ todo.type }} · {{ todo.time }}</small></div>
          </router-link>
          <el-empty v-if="!data.todos?.length" description="暂时没有待办" :image-size="70" />
        </div>
      </article>

      <article class="panel">
        <div class="panel-head"><div><h3>订单构成</h3><p>按业务类型统计</p></div><strong>{{ data.total_orders || 0 }} 单</strong></div>
        <div class="composition-list composition-pill-list">
          <div v-for="item in compositionRows" :key="item.label">
            <span><i></i>{{ item.label }}</span>
            <el-progress :percentage="item.percent" :stroke-width="9" color="#16834b" />
            <strong>{{ item.value }} 单</strong>
          </div>
          <el-empty v-if="!compositionRows.length" description="暂无订单" :image-size="70" />
        </div>
      </article>

      <article class="panel alert-panel">
        <div class="panel-head"><div><h3>合同到期提醒</h3><p>默认查看 45 天内到期合同</p></div><router-link to="/module/finance/contract">合同管理</router-link></div>
        <div class="alert-list">
          <div v-for="item in data.contract_alerts" :key="item.id">
            <strong>{{ item.contract_no }}｜{{ item.name }}</strong>
            <span>{{ item.end_date }} · {{ item.time }} · {{ money(item.amount) }}</span>
          </div>
          <el-empty v-if="!data.contract_alerts?.length" description="暂无快到期合同" :image-size="70" />
        </div>
      </article>

      <article class="panel alert-panel">
        <div class="panel-head"><div><h3>车辆提醒</h3><p>保险、年检、保养到期提醒</p></div><router-link to="/module/vehicle/list">车辆管理</router-link></div>
        <div class="alert-list">
          <div v-for="item in data.vehicle_alerts" :key="item.plate_no">
            <strong>{{ item.plate_no }}｜{{ item.status }}</strong>
            <span>{{ item.items }} <template v-if="item.reminder_to">· 提醒 {{ item.reminder_to }}</template></span>
          </div>
          <el-empty v-if="!data.vehicle_alerts?.length" description="暂无车辆提醒" :image-size="70" />
        </div>
      </article>

      <article class="panel schedule-overview">
        <div class="panel-head"><div><h3>今日/明日安排</h3><p>配送、换花、修剪打药等任务</p></div><router-link to="/module/schedule/list">每日安排</router-link></div>
        <el-table :data="data.schedules || []" size="small">
          <el-table-column prop="schedule_date" label="日期" width="105" />
          <el-table-column prop="planned_start" label="开始" width="70" />
          <el-table-column prop="task_type" label="类型" width="90" />
          <el-table-column prop="project_name" label="项目" min-width="150" show-overflow-tooltip />
          <el-table-column prop="item_summary" label="内容" min-width="220" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="90" />
        </el-table>
      </article>

      <article class="panel quick-panel">
        <div class="panel-head"><div><h3>快捷操作</h3><p>快速进入常用功能</p></div></div>
        <div class="quick-grid">
          <router-link to="/module/order/lease">新建租摆单</router-link>
          <router-link to="/module/purchase/list">采购单</router-link>
          <router-link to="/module/warehouse/list">出库配送</router-link>
          <router-link to="/module/report/project-cost">项目成本</router-link>
        </div>
      </article>
    </div>
  </div>
</template>
