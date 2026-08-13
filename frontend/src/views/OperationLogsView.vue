<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const loading = ref(false)
const rows = ref<Row[]>([])
const total = ref(0)
const filters = reactive({ keyword: '', module: '', action: '', limit: 100 })

const modules = computed(() => Array.from(new Set(rows.value.map((row) => row.module).filter(Boolean))))
const actions = computed(() => Array.from(new Set(rows.value.map((row) => row.action).filter(Boolean))))

function formatTime(value: string) {
  return String(value || '').replace('T', ' ').slice(0, 19)
}

async function loadRows() {
  loading.value = true
  try {
    const response = await api.get('/system/operation-logs', {
      params: {
        keyword: filters.keyword.trim(),
        module: filters.module || undefined,
        action: filters.action || undefined,
        limit: filters.limit,
      },
    })
    rows.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作日志加载失败')
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.keyword = ''
  filters.module = ''
  filters.action = ''
  filters.limit = 100
  loadRows()
}

onMounted(loadRows)
</script>

<template>
  <div class="page operation-logs-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">OPERATION LOG</p>
        <h1>操作日志</h1>
        <p>记录登录、账号维护、关键系统操作，方便以后追踪是谁在什么时候做了什么。</p>
      </div>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar">
        <el-input v-model="filters.keyword" clearable :prefix-icon="Search" placeholder="搜索账号、姓名、对象或说明" @keyup.enter="loadRows" @clear="loadRows" />
        <el-select v-model="filters.module" clearable placeholder="模块" @change="loadRows">
          <el-option v-for="item in modules" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.action" clearable placeholder="动作" @change="loadRows">
          <el-option v-for="item in actions" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.limit" style="width:105px" @change="loadRows">
          <el-option :value="50" label="50条" />
          <el-option :value="100" label="100条" />
          <el-option :value="200" label="200条" />
          <el-option :value="300" label="300条" />
        </el-select>
        <el-button type="success" plain :icon="Search" @click="loadRows">查询</el-button>
        <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
        <span class="crud-count">共 {{ total }} 条</span>
      </div>
      <el-table v-loading="loading" :data="rows" stripe border>
        <el-table-column label="时间" width="170" fixed>
          <template #default="scope">{{ formatTime(scope.row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="display_name" label="操作人" width="110">
          <template #default="scope">{{ scope.row.display_name || scope.row.username || '-' }}</template>
        </el-table-column>
        <el-table-column prop="username" label="账号" width="120" />
        <el-table-column prop="module" label="模块" width="105" />
        <el-table-column prop="action" label="动作" width="110" />
        <el-table-column prop="target_type" label="对象类型" width="105" />
        <el-table-column prop="target_name" label="对象" min-width="140" show-overflow-tooltip />
        <el-table-column prop="detail" label="说明" min-width="260" show-overflow-tooltip />
        <el-table-column prop="ip_address" label="IP" width="125" />
      </el-table>
    </article>
  </div>
</template>
