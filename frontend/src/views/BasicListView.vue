<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>
type Column = { prop: string; label: string; width?: number; minWidth?: number }

const route = useRoute()
const loading = ref(false)
const keyword = ref('')
const rows = ref<Row[]>([])
const total = ref(0)

const pageTitle = computed(() => String(route.meta.title || '数据列表'))
const endpoint = computed(() => String(route.meta.endpoint || ''))
const columns = computed<Column[]>(() => {
  const value = route.meta.columns
  return Array.isArray(value) ? value as Column[] : []
})

function valueText(row: Row, prop: string) {
  const value = row[prop]
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(2)))
  return String(value)
}

async function loadRows() {
  if (!endpoint.value) return
  loading.value = true
  try {
    const response = await api.get(endpoint.value, { params: { keyword: keyword.value.trim() || undefined } })
    const data = response.data
    rows.value = Array.isArray(data) ? data : data.items || []
    total.value = Number(data.total ?? rows.value.length)
  } catch (error: any) {
    rows.value = []
    total.value = 0
    ElMessage.error(error.response?.data?.detail || `${pageTitle.value}加载失败`)
  } finally {
    loading.value = false
  }
}

function reset() {
  keyword.value = ''
  loadRows()
}

watch(() => route.fullPath, loadRows)
onMounted(loadRows)
</script>

<template>
  <div class="page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">DATA LIST</p>
        <h1>{{ pageTitle }}</h1>
        <p>当前先恢复真实数据读取和搜索，新增、编辑、删除会继续按模块逐步补回。</p>
      </div>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar">
        <el-input
          v-model="keyword"
          clearable
          :prefix-icon="Search"
          placeholder="输入关键词搜索"
          @keyup.enter="loadRows"
          @clear="loadRows"
        />
        <el-button type="success" plain :icon="Search" @click="loadRows">查询</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
        <span class="table-count">共 {{ total }} 条</span>
      </div>

      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column
          v-for="column in columns"
          :key="column.prop"
          :prop="column.prop"
          :label="column.label"
          :width="column.width"
          :min-width="column.minWidth || 120"
          show-overflow-tooltip
        >
          <template #default="scope">{{ valueText(scope.row, column.prop) }}</template>
        </el-table-column>
      </el-table>
    </article>
  </div>
</template>

