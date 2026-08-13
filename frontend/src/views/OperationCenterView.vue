<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Bell, Calendar, Check, Coin, Refresh, Van, Warning } from '@element-plus/icons-vue'
import type { Component } from 'vue'
import { api } from '../api/client'

type Row = Record<string, any>

const loading = ref(false)
const data = ref<Row>({ todos: [], schedules: [], contract_alerts: [], vehicle_alerts: [], finance: {}, metrics: [] })
const activeType = ref('全部')
const typeOptions = ['全部', '审批', '采购', '应收', '合同', '车辆', '日程']

function money(value: unknown) {
  return `¥${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`
}

function tagType(type: string) {
  if (type.includes('审批')) return 'warning'
  if (type.includes('采购')) return 'success'
  if (type.includes('应收')) return 'danger'
  if (type.includes('合同')) return 'primary'
  if (type.includes('车辆')) return 'info'
  return 'success'
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

const reminderRows = computed(() => {
  const rows: Row[] = []
  for (const item of data.value.todos || []) {
    rows.push({
      type: item.type || '待办',
      title: item.title,
      desc: item.time || '待处理',
      path: item.path || '/',
      level: item.type === '应收' ? '高' : item.type === '审批' ? '中' : '普通',
    })
  }
  for (const item of data.value.contract_alerts || []) {
    rows.push({
      type: '合同',
      title: `${item.contract_no}｜${item.name}`,
      desc: `${item.end_date} · ${item.time} · ${money(item.amount)}`,
      path: '/module/finance/contract',
      level: item.time?.includes('今天') || item.time?.includes('已过期') ? '高' : '中',
    })
  }
  for (const item of data.value.vehicle_alerts || []) {
    rows.push({
      type: '车辆',
      title: `${item.plate_no}｜${item.status}`,
      desc: `${item.items || '车辆提醒'}${item.reminder_to ? ` · 提醒 ${item.reminder_to}` : ''}`,
      path: '/module/vehicle/list',
      level: item.status === '已过期' ? '高' : '中',
    })
  }
  for (const item of data.value.schedules || []) {
    rows.push({
      type: '日程',
      title: `${item.schedule_date} ${item.planned_start || ''}｜${item.task_type}`,
      desc: `${item.project_name || '未指定项目'} · ${item.item_summary || '待安排内容'}`,
      path: '/module/schedule/list',
      level: item.status === '待执行' ? '中' : '普通',
    })
  }
  return rows
})

const filteredRows = computed(() => {
  if (activeType.value === '全部') return reminderRows.value
  return reminderRows.value.filter((row) => String(row.type).includes(activeType.value))
})

const summaryCards = computed(() => [
  { label: '总提醒', value: reminderRows.value.length, sub: '所有待关注事项', color: 'blue', icon: Bell },
  { label: '待审批/采购', value: Number(data.value.metrics?.[0]?.value || 0) + Number(data.value.metrics?.[2]?.value || 0), sub: '需要内部处理', color: 'orange', icon: Warning },
  { label: '今日/明日日程', value: data.value.schedules?.length || 0, sub: '配送养护安排', color: 'green', icon: Calendar },
  { label: '车辆提醒', value: data.value.vehicle_alerts?.length || 0, sub: '保险年检保养', color: 'purple', icon: Van },
] as Array<{ label: string; value: number; sub: string; color: string; icon: Component }>)

const urgentCount = computed(() => reminderRows.value.filter((row) => row.level === '高').length)
const normalCount = computed(() => Math.max(0, reminderRows.value.length - urgentCount.value))
const receivableRate = computed(() => {
  const total = Number(data.value.finance?.receivable_total || 0)
  const received = Number(data.value.finance?.received_total || 0)
  return total ? Math.round(received / total * 100) : 0
})
</script>

<template>
  <div v-loading="loading" class="page operation-center-page">
    <div class="operation-hero">
      <div>
        <p class="eyebrow">OPERATION CENTER</p>
        <h1>运营提醒中心</h1>
        <p>把审批、采购、收款、合同、车辆和日程提醒集中到一起，主管和客服每天先看这里。</p>
        <div class="operation-hero-actions">
          <router-link to="/module/workflow/progress">处理审批</router-link>
          <router-link to="/module/schedule/list">查看安排表</router-link>
          <button @click="loadData"><el-icon><Refresh /></el-icon>刷新</button>
        </div>
      </div>
      <div class="operation-hero-gauge">
        <div class="gauge-ring big" :style="{ '--rate': `${receivableRate}%` }">
          <strong>{{ receivableRate }}%</strong>
          <span>回款率</span>
        </div>
      </div>
    </div>

    <div class="operation-summary-grid">
      <article v-for="card in summaryCards" :key="card.label" class="operation-summary-card" :class="`op-${card.color}`">
        <el-icon><component :is="card.icon" /></el-icon>
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
        <small>{{ card.sub }}</small>
      </article>
    </div>

    <div class="operation-grid">
      <article class="panel operation-main-list">
        <div class="operation-panel-head">
          <div>
            <h3>提醒事项</h3>
            <p>按类型筛选，点击即可进入对应业务页面。</p>
          </div>
          <div class="operation-filter">
            <button v-for="item in typeOptions" :key="item" :class="{ active: activeType === item }" @click="activeType = item">{{ item }}</button>
          </div>
        </div>

        <div class="reminder-list">
          <router-link v-for="row in filteredRows" :key="`${row.type}-${row.title}-${row.desc}`" class="reminder-item" :to="row.path">
            <div class="reminder-mark" :class="`level-${row.level}`"><el-icon><Warning v-if="row.level === '高'" /><Check v-else /></el-icon></div>
            <div>
              <div class="reminder-title"><strong>{{ row.title }}</strong><el-tag size="small" :type="tagType(row.type)">{{ row.type }}</el-tag></div>
              <p>{{ row.desc }}</p>
            </div>
            <span class="reminder-level">{{ row.level }}</span>
          </router-link>
          <el-empty v-if="!filteredRows.length" description="当前分类没有提醒" :image-size="80" />
        </div>
      </article>

      <aside class="operation-side">
        <article class="panel operation-radar">
          <div class="operation-panel-head">
            <div><h3>风险仪表</h3><p>红色事项越多，越需要优先处理。</p></div>
          </div>
          <div class="risk-orbit">
            <div class="risk-core"><strong>{{ urgentCount }}</strong><span>紧急</span></div>
            <span class="orbit-dot dot-a">审批</span>
            <span class="orbit-dot dot-b">合同</span>
            <span class="orbit-dot dot-c">车辆</span>
            <span class="orbit-dot dot-d">收款</span>
          </div>
          <div class="risk-split">
            <div><span>普通事项</span><strong>{{ normalCount }}</strong></div>
            <div><span>未收款</span><strong>{{ money(data.finance?.unreceived_total) }}</strong></div>
          </div>
        </article>

        <article class="panel operation-schedules">
          <div class="operation-panel-head">
            <div><h3>近期安排</h3><p>今日和明日需要执行的任务。</p></div>
          </div>
          <div class="schedule-mini-list">
            <router-link v-for="item in data.schedules" :key="item.id" to="/module/schedule/list">
              <b>{{ item.planned_start || '待定' }}</b>
              <span>{{ item.project_name || '未指定项目' }}</span>
              <small>{{ item.task_type }} · {{ item.status }}</small>
            </router-link>
            <el-empty v-if="!data.schedules?.length" description="暂无近期安排" :image-size="70" />
          </div>
        </article>
      </aside>
    </div>
  </div>
</template>
