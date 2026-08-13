<script setup lang="ts">
import { computed, ref } from 'vue'
import { Check, Location, Refresh, Search, Van } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../../api/client'

type Row = Record<string, any>

const loading = ref(false)
const keyword = ref('')
const selectedDate = ref(new Date().toISOString().slice(0, 10))
const includeDone = ref(true)
const rows = ref<Row[]>([])

const pendingRows = computed(() => rows.value.filter((row) => !['已完成', '已取消'].includes(row.status)))

function nextActions(row: Row) {
  if (row.status === '已发布') return [{ label: '开始配送', status: '配送中', type: 'warning', icon: Van }]
  if (row.status === '已出库' || row.status === '配送中') return [{ label: '已送达', status: '已送达', type: 'primary', icon: Location }]
  if (row.status === '已送达') return [{ label: '完成', status: '已完成', type: 'success', icon: Check }]
  return []
}

function timeText(row: Row) {
  return [row.planned_start, row.planned_end].filter(Boolean).join(' - ') || '未定时间'
}

async function loadRows() {
  loading.value = true
  try {
    rows.value = (await api.get('/schedules/my', {
      params: { schedule_date: selectedDate.value || undefined, keyword: keyword.value.trim(), include_done: includeDone.value },
    })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '任务加载失败')
  } finally {
    loading.value = false
  }
}

async function changeStatus(row: Row, status: string) {
  await ElMessageBox.confirm(`确认把“${row.task_no}”改为“${status}”吗？`, '任务确认', { type: 'warning' })
  try {
    await api.post(`/schedules/${row.id}/status`, { status })
    ElMessage.success(`任务已改为：${status}`)
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '任务状态修改失败')
  }
}

loadRows()
</script>

<template>
  <div class="mobile-page" v-loading="loading">
    <section class="mobile-title">
      <div><p>MY TASKS</p><h1>我的任务</h1></div>
      <button type="button" @click="loadRows"><el-icon><Refresh /></el-icon></button>
    </section>

    <section class="mobile-filter">
      <el-date-picker v-model="selectedDate" value-format="YYYY-MM-DD" @change="loadRows" />
      <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="搜索项目、单号、清单" @keyup.enter="loadRows" @clear="loadRows" />
      <el-checkbox v-model="includeDone" @change="loadRows">显示已完成</el-checkbox>
    </section>

    <section class="mobile-stat-line">
      <span>全部 {{ rows.length }}</span>
      <span>待处理 {{ pendingRows.length }}</span>
    </section>

    <section v-if="rows.length" class="mobile-task-list">
      <article v-for="row in rows" :key="row.id" class="mobile-task-card">
        <div class="task-card-head">
          <strong>{{ row.project_name || row.task_no }}</strong>
          <el-tag size="small">{{ row.status }}</el-tag>
        </div>
        <p>{{ row.task_type }}｜{{ row.schedule_date }}｜{{ timeText(row) }}</p>
        <p>{{ row.address || '未填地址' }}</p>
        <div class="task-items">{{ row.item_summary || '暂无任务清单' }}</div>
        <small>{{ [row.source_type, row.source_no].filter(Boolean).join('：') }}</small>
        <div class="task-actions">
          <el-button
            v-for="action in nextActions(row)"
            :key="action.status"
            :type="action.type"
            :icon="action.icon"
            @click="changeStatus(row, action.status)"
          >
            {{ action.label }}
          </el-button>
          <span v-if="!nextActions(row).length">无需操作</span>
        </div>
      </article>
    </section>
    <el-empty v-else description="暂无任务" :image-size="90" />
  </div>
</template>
