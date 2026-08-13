<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Calendar, Finished, Refresh, ShoppingCart, Van } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { api } from '../api/client'

type Row = Record<string, any>

const router = useRouter()
const loading = ref(false)
const data = ref<Row>({
  user: {},
  summary: {},
  role_cards: [],
  purchase_tasks: [],
  inbound_tasks: [],
  schedule_tasks: [],
  maintenance_tasks: [],
  maintenance_records: [],
})

async function loadData() {
  loading.value = true
  try {
    data.value = (await api.get('/dashboard/my-workbench')).data
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '我的工作台加载失败')
  } finally {
    loading.value = false
  }
}

function go(path: string) {
  if (path) router.push(path)
}

function taskTime(row: Row) {
  return [row.schedule_date, row.planned_start, row.planned_end].filter(Boolean).join(' ')
}

function emptyText(title: string) {
  return `暂无${title}`
}

onMounted(loadData)
</script>

<template>
  <div class="page my-workbench-page" v-loading="loading">
    <div class="page-heading compact workbench-hero">
      <div>
        <p class="eyebrow">MY WORKBENCH</p>
        <h1>{{ data.user?.display_name || '我的工作台' }}</h1>
        <p>
          {{ data.user?.department || '绿风管理软件' }}
          <span v-if="data.user?.position"> · {{ data.user.position }}</span>
          <span v-if="data.user?.role"> · {{ data.user.role }}</span>
        </p>
      </div>
      <el-button type="success" :icon="Refresh" @click="loadData">刷新任务</el-button>
    </div>

    <section class="workbench-cards">
      <button v-for="card in data.role_cards" :key="card.label" type="button" class="workbench-card" @click="go(card.path)">
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
        <small>{{ card.hint }}</small>
      </button>
    </section>

    <section class="workbench-grid">
      <article class="panel workbench-panel">
        <div class="panel-title">
          <div><el-icon><ShoppingCart /></el-icon><strong>我的采购任务</strong></div>
          <el-button link type="success" @click="go('/module/purchase/my')">进入采购</el-button>
        </div>
        <div v-if="data.purchase_tasks?.length" class="task-list">
          <div v-for="row in data.purchase_tasks" :key="row.id" class="task-row" @click="go(row.path)">
            <div><strong>{{ row.order_no }}</strong><span>{{ row.supplier || '未填供应商' }}</span></div>
            <el-tag size="small" type="warning">{{ row.status }}</el-tag>
            <small>{{ row.purchase_date || '未定日期' }} · {{ row.purchaser || '自动接单' }}</small>
          </div>
        </div>
        <el-empty v-else :description="emptyText('采购任务')" :image-size="70" />
      </article>

      <article class="panel workbench-panel">
        <div class="panel-title">
          <div><el-icon><Finished /></el-icon><strong>仓库入库任务</strong></div>
          <el-button link type="success" @click="go('/module/inventory/inbound')">进入入库</el-button>
        </div>
        <div v-if="data.inbound_tasks?.length" class="task-list">
          <div v-for="row in data.inbound_tasks" :key="row.id" class="task-row" @click="go(row.path)">
            <div><strong>{{ row.order_no }}</strong><span>{{ row.supplier || '采购入库' }}</span></div>
            <el-tag size="small" type="success">{{ row.status }}</el-tag>
            <small>{{ row.purchase_date || '未定日期' }} · {{ row.purchaser || '自动接单' }}</small>
          </div>
        </div>
        <el-empty v-else :description="emptyText('入库任务')" :image-size="70" />
      </article>

      <article class="panel workbench-panel">
        <div class="panel-title">
          <div><el-icon><Van /></el-icon><strong>我的配送/日程</strong></div>
          <el-button link type="success" @click="go('/module/schedule/list')">进入安排表</el-button>
        </div>
        <div v-if="data.schedule_tasks?.length" class="task-list">
          <div v-for="row in data.schedule_tasks" :key="row.id" class="task-row" @click="go(row.path)">
            <div><strong>{{ row.project_name || row.task_no }}</strong><span>{{ row.task_type }} · {{ row.address || '未填地址' }}</span></div>
            <el-tag size="small" type="primary">{{ row.status }}</el-tag>
            <small>{{ taskTime(row) || '未定时间' }} · {{ row.item_summary || '无清单' }}</small>
          </div>
        </div>
        <el-empty v-else :description="emptyText('配送/日程')" :image-size="70" />
      </article>

      <article class="panel workbench-panel">
        <div class="panel-title">
          <div><el-icon><Calendar /></el-icon><strong>养护计划</strong></div>
          <el-button link type="success" @click="go('/module/maintenance/manage')">进入养护</el-button>
        </div>
        <div v-if="data.maintenance_tasks?.length" class="task-list">
          <div v-for="row in data.maintenance_tasks" :key="row.id" class="task-row" @click="go(row.path)">
            <div><strong>{{ row.project_name }}</strong><span>{{ row.area_description || '全部区域' }}</span></div>
            <el-tag size="small" type="success">{{ row.status }}</el-tag>
            <small>下次：{{ row.next_due_date || '未设置' }} · {{ row.service_content || '未填养护内容' }}</small>
          </div>
        </div>
        <el-empty v-else :description="emptyText('养护计划')" :image-size="70" />
      </article>
    </section>

    <article class="panel workbench-panel">
      <div class="panel-title">
        <div><el-icon><Calendar /></el-icon><strong>最近养护记录</strong></div>
      </div>
      <el-table :data="data.maintenance_records || []" stripe empty-text="暂无养护记录">
        <el-table-column prop="service_date" label="日期" width="110" />
        <el-table-column prop="record_no" label="记录号" width="145" />
        <el-table-column prop="project_name" label="项目" min-width="160" />
        <el-table-column prop="area_description" label="区域" min-width="150" />
        <el-table-column prop="site_issue" label="现场问题" min-width="180" show-overflow-tooltip />
        <el-table-column prop="handle_result" label="处理结果" min-width="180" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="90" />
      </el-table>
    </article>
  </div>
</template>

<style scoped>
.workbench-hero {
  background:
    radial-gradient(circle at 88% 12%, rgba(34, 197, 94, .16), transparent 28%),
    linear-gradient(135deg, #eff6ff 0%, #f7fee7 100%);
}

.workbench-cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.workbench-card {
  border: 0;
  border-radius: 22px;
  padding: 18px;
  text-align: left;
  background: linear-gradient(135deg, #ffffff 0%, #ecfeff 100%);
  box-shadow: 0 16px 35px rgba(15, 23, 42, .08);
  cursor: pointer;
}

.workbench-card span,
.workbench-card small {
  display: block;
  color: #64748b;
}

.workbench-card strong {
  display: block;
  color: #0f766e;
  font-size: 32px;
  line-height: 1.2;
  margin: 8px 0;
}

.workbench-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.workbench-panel {
  padding: 18px;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.panel-title > div {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-list {
  display: grid;
  gap: 10px;
}

.task-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 6px 10px;
  align-items: center;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 12px;
  cursor: pointer;
  background: #fff;
}

.task-row:hover {
  border-color: #86efac;
  background: #f7fee7;
}

.task-row div span,
.task-row small {
  display: block;
  color: #64748b;
  margin-top: 4px;
}

.task-row small {
  grid-column: 1 / -1;
}

@media (max-width: 980px) {
  .workbench-cards,
  .workbench-grid {
    grid-template-columns: 1fr;
  }
}
</style>
