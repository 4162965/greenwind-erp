<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { api } from '../../api/client'

type Row = Record<string, any>
type Tone = 'leaf' | 'sky' | 'sun' | 'rose' | 'violet' | 'aqua' | 'stone'

const router = useRouter()
const loading = ref(false)
const data = ref<Row>({ user: {}, summary: {}, schedule_tasks: [], maintenance_tasks: [], purchase_tasks: [], inbound_tasks: [] })

const colors: Record<Tone, [string, string, string]> = {
  leaf: ['#ecfff4', '#52d991', '#0f9f68'],
  sky: ['#eff9ff', '#62c7f2', '#2682d9'],
  sun: ['#fff8df', '#ffd66e', '#ee9b11'],
  rose: ['#fff0ec', '#ffad8f', '#ef6d45'],
  violet: ['#f5f0ff', '#b89cff', '#7557d7'],
  aqua: ['#eafffb', '#4dd7cc', '#0f9b8f'],
  stone: ['#f3f7f8', '#a9bdc8', '#607480'],
}

function picture(kind: string, tone: Tone) {
  const [bg, main, dark] = colors[tone]
  const white = '#fff'
  const drawings: Record<string, string> = {
    order: `<rect x="20" y="25" width="52" height="44" rx="10" fill="${white}"/><path d="M31 38h23M31 50h33M31 62h23" stroke="${dark}" stroke-width="5" stroke-linecap="round"/><path d="M61 25h8a8 8 0 0 1 8 8v10H61z" fill="${main}"/>`,
    add: `<rect x="22" y="27" width="52" height="43" rx="13" fill="${white}"/><path d="M48 37v24M36 49h24" stroke="${dark}" stroke-width="7" stroke-linecap="round"/><circle cx="69" cy="29" r="12" fill="${main}"/>`,
    flower: `<path d="M34 58h29l-5 19H39z" fill="${dark}"/><path d="M48 55V30" stroke="${dark}" stroke-width="5" stroke-linecap="round"/><path d="M48 42c-14-9-24-7-31 4 12 5 23 2 31-4z" fill="#8beeb9"/><path d="M48 37c11-11 22-13 31-5-8 10-19 13-31 5z" fill="${main}"/>`,
    care: `<path d="M34 74c-10-10-12-27-1-41 13 10 16 25 1 41z" fill="#61dda0"/><path d="M55 72c-9-10-7-25 10-38 8 16 4 29-10 38z" fill="${dark}"/><path d="M70 24c8 12 12 19 12 26a14 14 0 0 1-28 0c0-7 7-17 16-26z" fill="${main}"/>`,
    task: `<rect x="20" y="24" width="56" height="50" rx="13" fill="${white}"/><path d="M33 41l7 7 14-16M33 60h28" stroke="${dark}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="68" cy="60" r="8" fill="${main}"/>`,
    calendar: `<rect x="18" y="24" width="60" height="52" rx="13" fill="${white}"/><rect x="18" y="24" width="60" height="17" rx="13" fill="${main}"/><path d="M33 20v12M63 20v12" stroke="${dark}" stroke-width="5" stroke-linecap="round"/><rect x="30" y="51" width="13" height="10" rx="4" fill="${main}"/><rect x="52" y="51" width="15" height="10" rx="4" fill="${dark}"/>`,
    goods: `<path d="M28 37h41l-5 33H33z" fill="${white}"/><path d="M37 39c0-10 5-17 13-17s13 7 13 17" fill="none" stroke="${dark}" stroke-width="5" stroke-linecap="round"/><path d="M42 58h17" stroke="${main}" stroke-width="6" stroke-linecap="round"/>`,
    stock: `<rect x="16" y="47" width="30" height="25" rx="7" fill="${white}"/><rect x="50" y="47" width="30" height="25" rx="7" fill="${main}"/><rect x="33" y="25" width="30" height="25" rx="7" fill="${dark}"/>`,
    truck: `<rect x="17" y="39" width="43" height="22" rx="8" fill="${main}"/><path d="M60 45h11l9 10v6H60z" fill="${white}"/><circle cx="32" cy="65" r="7" fill="${dark}"/><circle cx="68" cy="65" r="7" fill="${dark}"/>`,
    project: `<rect x="20" y="24" width="26" height="50" rx="7" fill="${white}"/><rect x="50" y="34" width="26" height="40" rx="7" fill="${main}"/><path d="M29 35h7M29 47h7M59 46h7M59 58h7" stroke="${dark}" stroke-width="4" stroke-linecap="round"/>`,
    money: `<rect x="18" y="29" width="60" height="40" rx="12" fill="${white}"/><circle cx="48" cy="49" r="13" fill="${main}"/><path d="M48 40v18M41 49h14" stroke="${white}" stroke-width="4" stroke-linecap="round"/>`,
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96"><rect width="96" height="96" rx="26" fill="${bg}"/><circle cx="76" cy="18" r="18" fill="${main}" opacity=".18"/><circle cx="18" cy="80" r="22" fill="${white}" opacity=".62"/><g>${drawings[kind] || drawings.order}</g></svg>`
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

function moduleItem(title: string, path: string, kind: string, tone: Tone, count?: number) {
  return { title, path, kind, tone, count, image: picture(kind, tone) }
}

const taskCount = computed(() => data.value.schedule_tasks?.length || 0)
const exchangeCount = computed(() => data.value.maintenance_tasks?.length || 0)
const purchaseCount = computed(() => data.value.purchase_tasks?.length || 0)

const quickActions = computed(() => [
  { title: '手机下单', desc: '租摆、工程、电网、保洁', path: '/mobile/order/new', kind: 'add', tone: 'leaf' as Tone },
  { title: '新建商品', desc: '植物、花盆、药肥工具', path: '/mobile/goods/new', kind: 'goods', tone: 'sun' as Tone },
])

const moduleGroups = computed(() => [
  {
    title: '现场工作',
    modules: [
      moduleItem('换花报单', '/mobile/exchange', 'flower', 'leaf', exchangeCount.value),
      moduleItem('养护记录', '/mobile/maintenance', 'care', 'aqua', exchangeCount.value),
      moduleItem('我的任务', '/mobile/tasks', 'task', 'sky', taskCount.value),
      moduleItem('日程安排', '/mobile/tasks', 'calendar', 'violet', taskCount.value),
    ],
  },
  {
    title: '仓配采购',
    modules: [
      moduleItem('采购管理', '/mobile/purchases', 'goods', 'rose', purchaseCount.value),
      moduleItem('商品库存', '/mobile/inventory', 'stock', 'violet'),
      moduleItem('仓库配货', '/mobile/outbound', 'stock', 'aqua', data.value.inbound_tasks?.length || 0),
      moduleItem('车辆记录', '/mobile/list/vehicles', 'truck', 'stone'),
    ],
  },
  {
    title: '资料报表',
    modules: [
      moduleItem('客户项目', '/mobile/list/projects', 'project', 'sky'),
      moduleItem('项目植物', '/mobile/list/project-plants', 'flower', 'leaf'),
      moduleItem('订单进度', '/mobile/list/orders', 'order', 'rose'),
      moduleItem('费用报表', '/mobile/list/reports', 'money', 'sun'),
    ],
  },
])

async function loadData() {
  loading.value = true
  try {
    data.value = (await api.get('/dashboard/my-workbench')).data
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '移动工作台加载失败')
  } finally {
    loading.value = false
  }
}

function go(path: string) {
  router.push(path)
}

onMounted(loadData)
</script>

<template>
  <div class="mobile-page mobile-workbench fresh-workbench" v-loading="loading">
    <section class="fresh-hero">
      <div class="fresh-hero-copy">
        <p>GREENWIND</p>
        <h1>绿风工作台</h1>
        <span>{{ data.user?.display_name || '绿风员工' }}，今天也把现场安排得清清爽爽。</span>
      </div>
      <button type="button" class="fresh-refresh" @click="loadData"><el-icon><Refresh /></el-icon></button>
      <div class="fresh-hero-leaf one"></div>
      <div class="fresh-hero-leaf two"></div>
    </section>

    <section class="fresh-stats">
      <div><strong>{{ taskCount }}</strong><span>今日任务</span></div>
      <div><strong>{{ exchangeCount }}</strong><span>待处理报单</span></div>
      <div><strong>{{ purchaseCount }}</strong><span>采购任务</span></div>
    </section>

    <section class="fresh-quick-grid">
      <button v-for="item in quickActions" :key="item.title" type="button" class="fresh-quick-card" @click="go(item.path)">
        <img :src="picture(item.kind, item.tone)" :alt="item.title" />
        <strong>{{ item.title }}</strong>
        <span>{{ item.desc }}</span>
      </button>
    </section>

    <section v-for="group in moduleGroups" :key="group.title" class="fresh-module-card">
      <div class="fresh-section-title">
        <strong>{{ group.title }}</strong>
        <span>常用入口</span>
      </div>
      <div class="fresh-module-grid">
        <button
          v-for="item in group.modules"
          :key="item.title"
          type="button"
          class="fresh-module"
          @click="go(item.path)"
        >
          <span class="fresh-module-image"><img :src="item.image" :alt="item.title" /></span>
          <span>{{ item.title }}</span>
          <em v-if="item.count">{{ item.count }}</em>
        </button>
      </div>
    </section>
  </div>
</template>
