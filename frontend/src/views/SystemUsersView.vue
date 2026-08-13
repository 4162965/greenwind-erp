<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ArrowDown, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'
import { permissionOptions } from '../config/menu'

type Row = Record<string, any>

const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const rows = ref<Row[]>([])
const categories = ref<string[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<Row>({})

const activeCount = computed(() => rows.value.filter((row) => row.is_active).length)

function resetForm(values: Row) {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, values)
}

function permissionArray(value: string | string[] | undefined) {
  if (Array.isArray(value)) return value
  return String(value || '').split(',').map((item) => item.trim()).filter(Boolean)
}

function emptyUser() {
  return {
    username: '',
    display_name: '',
    role: '鍛樺伐',
    module_permissions: [],
    product_category_permissions: [],
    password: '123456',
    is_active: true,
  }
}

async function loadRows() {
  loading.value = true
  try {
    rows.value = (await api.get('/system/users', { params: { keyword: keyword.value.trim() } })).data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '璐﹀彿鍔犺浇澶辫触')
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  try {
    categories.value = (await api.get('/products/categories')).data.items || []
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鍟嗗搧鍒嗙被鍔犺浇澶辫触')
  }
}

function openCreate() {
  editingId.value = null
  resetForm(emptyUser())
  dialogVisible.value = true
}

function openEdit(row: Row) {
  editingId.value = row.id
  resetForm({
    ...row,
    module_permissions: permissionArray(row.module_permissions),
    product_category_permissions: permissionArray(row.product_category_permissions),
    password: '',
  })
  dialogVisible.value = true
}

async function saveUser() {
  if (!form.username || !form.display_name) {
    ElMessage.warning('璇峰～鍐欒处鍙峰拰鏄剧ず鍚嶇О')
    return
  }
  if (!editingId.value && !form.password) {
    ElMessage.warning('鏂拌处鍙疯濉啓鍒濆瀵嗙爜')
    return
  }
  saving.value = true
  try {
    const payload: Row = {
      ...form,
      module_permissions: (form.module_permissions || []).join(','),
      product_category_permissions: (form.product_category_permissions || []).join(','),
    }
    if (editingId.value && !payload.password) delete payload.password
    if (editingId.value) await api.put(`/system/users/${editingId.value}`, payload)
    else await api.post('/system/users', payload)
    ElMessage.success(`璐﹀彿宸?{editingId.value ? '淇敼' : '鏂板'}`)
    dialogVisible.value = false
    await loadRows()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '璐﹀彿淇濆瓨澶辫触')
  } finally {
    saving.value = false
  }
}

function formatTime(value: string) {
  return String(value || '').replace('T', ' ').slice(0, 16)
}

function formatProductCategoryPermissions(value: string) {
  return value ? value : '鏈崟鐙檺鍒?
}

onMounted(() => {
  loadRows()
  loadCategories()
})
</script>

<template>
  <div class="page system-users-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">SYSTEM ACCOUNT</p>
        <h1>绯荤粺璐﹀彿</h1>
        <p>缁存姢鍙櫥褰曠數鑴戠鍜屾墜鏈虹鐨勮处鍙枫€佽彍鍗曟潈闄愩€佸晢鍝佸垎绫讳簩绾ф潈闄愬拰鍚敤鐘舵€侊紱鍛樺伐璐﹀彿寤鸿缁熶竴浣跨敤鎵嬫満鍙枫€?/p>
      </div>
      <el-button type="success" :icon="Plus" @click="openCreate">鏂板璐﹀彿</el-button>
    </div>

    <div class="inventory-summary report-summary-cards">
      <div><span>璐﹀彿鎬绘暟</span><strong>{{ rows.length }}</strong></div>
      <div><span>鍚敤璐﹀彿</span><strong>{{ activeCount }}</strong></div>
      <div><span>鍋滅敤璐﹀彿</span><strong>{{ rows.length - activeCount }}</strong></div>
      <div><span>鍟嗗搧鍒嗙被</span><strong>{{ categories.length }}</strong></div>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar">
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="鎼滅储璐﹀彿銆佸悕绉版垨瑙掕壊" @keyup.enter="loadRows" @clear="loadRows" />
        <el-button type="success" plain :icon="Search" @click="loadRows">鏌ヨ</el-button>
        <el-button :icon="Refresh" @click="keyword=''; loadRows()">閲嶇疆</el-button>
      </div>
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="username" label="璐﹀彿" min-width="130" fixed />
        <el-table-column prop="display_name" label="鏄剧ず鍚嶇О" min-width="120" />
        <el-table-column prop="role" label="绯荤粺韬唤" width="105" />
        <el-table-column label="鑿滃崟鏉冮檺" min-width="260" show-overflow-tooltip>
          <template #default="scope">
            <span v-if="!scope.row.module_permissions">鎸夎韩浠介粯璁?/span>
            <span v-else>{{ scope.row.module_permissions }}</span>
          </template>
        </el-table-column>
        <el-table-column label="鍟嗗搧鍒嗙被鏉冮檺" min-width="180" show-overflow-tooltip>
          <template #default="scope">{{ formatProductCategoryPermissions(scope.row.product_category_permissions) }}</template>
        </el-table-column>
        <el-table-column label="鐘舵€? width="90">
          <template #default="scope">
            <el-tag :type="scope.row.is_active ? 'success' : 'info'" size="small">{{ scope.row.is_active ? '鍚敤' : '鍋滅敤' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="鍒涘缓鏃堕棿" width="160">
          <template #default="scope">{{ formatTime(scope.row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="鎿嶄綔" width="90">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :icon="Edit" @click="openEdit(scope.row)">缂栬緫</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <el-dialog v-model="dialogVisible" :title="editingId ? '缂栬緫璐﹀彿' : '鏂板璐﹀彿'" width="760px" destroy-on-close>
      <el-form label-position="top" class="foundation-form">
        <el-form-item label="鐧诲綍璐﹀彿" required>
          <el-input v-model="form.username" :disabled="!!editingId" placeholder="鍛樺伐璐﹀彿璇峰～鍐欐墜鏈哄彿" />
        </el-form-item>
        <el-form-item label="鏄剧ず鍚嶇О" required>
          <el-input v-model="form.display_name" />
        </el-form-item>
        <el-form-item label="绯荤粺韬唤">
          <el-input v-model="form.role" placeholder="渚嬪锛氱鐞嗗憳銆佺粡鐞嗐€佸鏈嶃€佸吇鎶ゅ憳銆佸徃鏈? />
        </el-form-item>
        <el-form-item :label="editingId ? '閲嶇疆瀵嗙爜' : '鍒濆瀵嗙爜'">
          <el-input v-model="form.password" type="password" show-password :placeholder="editingId ? '闇€瑕侀噸缃椂濉啓锛涗笉濉〃绀轰笉鏀瑰瘑鐮? : '榛樿 123456'" />
        </el-form-item>
        <el-form-item label="妯″潡鏉冮檺">
          <el-select v-model="form.module_permissions" multiple clearable collapse-tags collapse-tags-tooltip style="width:100%" placeholder="涓嶉€夊垯鎸夎韩浠介粯璁?>
            <el-option v-for="item in permissionOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="鍟嗗搧绠＄悊浜岀骇鏉冮檺锛氬晢鍝佸垎绫?>
          <el-select v-model="form.product_category_permissions" multiple clearable collapse-tags collapse-tags-tooltip style="width:100%" placeholder="閫夋嫨璇ヨ处鍙峰厑璁告煡鐪?閫夋嫨鐨勫晢鍝佸垎绫?>
            <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
          </el-select>
          <div class="field-help">杩欎釜鏄晢鍝佺鐞嗕笅闈㈢殑浜岀骇鏉冮檺銆傚彧缁欐煇浜涘垎绫诲悗锛岃璐﹀彿鍦ㄥ晢鍝佸垪琛ㄣ€佷笅鍗曢€夊晢鍝佹椂鍙兘鐪嬪埌杩欎簺鍒嗙被锛涗笉閫夎〃绀轰笉鍗曠嫭闄愬埗銆?/div>
        </el-form-item>
        <el-form-item label="鍚敤鐘舵€?>
          <el-switch v-model="form.is_active" active-text="鍚敤" inactive-text="鍋滅敤" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">鍙栨秷</el-button>
        <el-button type="success" :loading="saving" @click="saveUser">淇濆瓨</el-button>
      </template>
    </el-dialog>
  </div>
</template>

