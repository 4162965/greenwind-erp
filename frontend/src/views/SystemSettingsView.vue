<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Delete, Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'
import { DEFAULT_DEPARTMENTS, getDepartmentOptions, saveDepartmentOptions } from '../utils/departments'
import { DEFAULT_POSITIONS, getPositionOptions, savePositionOptions } from '../utils/positions'
import { DEFAULT_UNITS, getUnitOptions, saveUnitOptions } from '../utils/units'

const units = ref<string[]>(getUnitOptions())
const newUnit = ref('')
const positions = ref<string[]>(getPositionOptions())
const newPosition = ref('')
const departments = ref<string[]>(getDepartmentOptions())
const newDepartment = ref('')
const categories = ref<string[]>([])
const newCategory = ref('')

function persistUnits(message = '单位设置已保存') {
  saveUnitOptions(units.value)
  ElMessage.success(message)
}

function addUnit() {
  const value = newUnit.value.trim()
  if (!value) { ElMessage.warning('请输入单位名称'); return }
  if (units.value.includes(value)) { ElMessage.warning('这个单位已经存在'); return }
  units.value.push(value)
  newUnit.value = ''
  persistUnits('单位添加成功')
}

async function removeUnit(unit: string) {
  await ElMessageBox.confirm(`确定删除单位“${unit}”吗？`, '删除确认', { type: 'warning' })
  units.value = units.value.filter((item) => item !== unit)
  persistUnits('单位删除成功')
}

function restoreDefaultUnits() {
  units.value = [...DEFAULT_UNITS]
  persistUnits('已恢复默认单位')
}

function persistPositions(message = '岗位设置已保存') {
  savePositionOptions(positions.value)
  ElMessage.success(message)
}

function addPosition() {
  const value = newPosition.value.trim()
  if (!value) { ElMessage.warning('请输入岗位名称'); return }
  if (positions.value.includes(value)) { ElMessage.warning('这个岗位已经存在'); return }
  positions.value.push(value)
  newPosition.value = ''
  persistPositions('岗位添加成功')
}

async function removePosition(position: string) {
  await ElMessageBox.confirm(`确定删除岗位“${position}”吗？已使用该岗位的员工资料不会自动清空。`, '删除确认', { type: 'warning' })
  positions.value = positions.value.filter((item) => item !== position)
  persistPositions('岗位删除成功')
}

function restoreDefaultPositions() {
  positions.value = [...DEFAULT_POSITIONS]
  persistPositions('已恢复默认岗位')
}

function persistDepartments(message = '部门设置已保存') {
  saveDepartmentOptions(departments.value)
  ElMessage.success(message)
}

function addDepartment() {
  const value = newDepartment.value.trim()
  if (!value) { ElMessage.warning('请输入部门名称'); return }
  if (departments.value.includes(value)) { ElMessage.warning('这个部门已经存在'); return }
  departments.value.push(value)
  newDepartment.value = ''
  persistDepartments('部门添加成功')
}

async function removeDepartment(department: string) {
  await ElMessageBox.confirm(`确定删除部门“${department}”吗？已使用该部门的员工资料不会自动清空。`, '删除确认', { type: 'warning' })
  departments.value = departments.value.filter((item) => item !== department)
  persistDepartments('部门删除成功')
}

function restoreDefaultDepartments() {
  departments.value = [...DEFAULT_DEPARTMENTS]
  persistDepartments('已恢复默认部门')
}

async function loadCategories() {
  try {
    const response = await api.get('/products/categories')
    categories.value = response.data.items || []
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '分类加载失败')
  }
}

async function addCategory() {
  const name = newCategory.value.trim()
  if (!name) { ElMessage.warning('请输入分类名称'); return }
  try {
    await api.post('/products/categories', { name })
    ElMessage.success('分类添加成功')
    newCategory.value = ''
    await loadCategories()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '分类添加失败')
  }
}

async function removeCategory(name: string) {
  await ElMessageBox.confirm(`确定删除分类“${name}”吗？如果该分类下已有商品，将不能删除。`, '删除确认', { type: 'warning' })
  try {
    await api.delete(`/products/categories/${encodeURIComponent(name)}`)
    ElMessage.success('分类删除成功')
    await loadCategories()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '分类删除失败')
  }
}

onMounted(loadCategories)
</script>

<template>
  <div class="page settings-page">
    <div class="page-heading compact">
      <div>
        <p class="eyebrow">SYSTEM SETTINGS</p>
        <h1>平台设置</h1>
        <p>维护商品分类、岗位、部门、单位等基础选项；员工档案会直接使用这里的岗位和部门。</p>
      </div>
    </div>

    <article class="panel settings-panel">
      <div class="panel-head">
        <div>
          <h3>商品分类管理</h3>
          <p>新建商品、手机下单、采购选商品都会使用这里的分类；账号可设置允许查看的分类。</p>
        </div>
        <el-button plain :icon="Refresh" @click="loadCategories">刷新</el-button>
      </div>

      <div class="unit-editor">
        <el-input v-model="newCategory" placeholder="输入新分类，例如：绿植、花盆、药肥" clearable @keyup.enter="addCategory" />
        <el-button type="success" :icon="Plus" @click="addCategory">添加分类</el-button>
      </div>

      <div class="unit-list">
        <div v-for="category in categories" :key="category" class="unit-chip">
          <span>{{ category }}</span>
          <el-button link type="danger" :icon="Delete" @click="removeCategory(category)" />
        </div>
      </div>
    </article>

    <article class="panel settings-panel">
      <div class="panel-head">
        <div>
          <h3>岗位管理</h3>
          <p>员工档案里的岗位从这里选择，例如司机、养护员、跟车配送人员、经理、主管等。</p>
        </div>
        <el-button plain @click="restoreDefaultPositions">恢复默认</el-button>
      </div>

      <div class="unit-editor">
        <el-input v-model="newPosition" placeholder="输入新岗位，例如：区域主管、临工" clearable @keyup.enter="addPosition" />
        <el-button type="success" :icon="Plus" @click="addPosition">添加岗位</el-button>
      </div>

      <div class="unit-list">
        <div v-for="position in positions" :key="position" class="unit-chip">
          <span>{{ position }}</span>
          <el-button link type="danger" :icon="Delete" @click="removePosition(position)" />
        </div>
      </div>
    </article>

    <article class="panel settings-panel">
      <div class="panel-head">
        <div>
          <h3>部门管理</h3>
          <p>员工档案里的部门从这里选择，例如市场部、绿化部、财务部、采购部、配送部等。</p>
        </div>
        <el-button plain @click="restoreDefaultDepartments">恢复默认</el-button>
      </div>

      <div class="unit-editor">
        <el-input v-model="newDepartment" placeholder="输入新部门，例如：工程部、售后部" clearable @keyup.enter="addDepartment" />
        <el-button type="success" :icon="Plus" @click="addDepartment">添加部门</el-button>
      </div>

      <div class="unit-list">
        <div v-for="department in departments" :key="department" class="unit-chip">
          <span>{{ department }}</span>
          <el-button link type="danger" :icon="Delete" @click="removeDepartment(department)" />
        </div>
      </div>
    </article>

    <article class="panel settings-panel">
      <div class="panel-head">
        <div>
          <h3>单位管理</h3>
          <p>新增或删除后，商品页面的单位下拉框会使用这里的列表。</p>
        </div>
        <el-button plain @click="restoreDefaultUnits">恢复默认</el-button>
      </div>

      <div class="unit-editor">
        <el-input v-model="newUnit" placeholder="输入新单位，例如：支、包、棵" clearable @keyup.enter="addUnit" />
        <el-button type="success" :icon="Plus" @click="addUnit">添加单位</el-button>
      </div>

      <div class="unit-list">
        <div v-for="unit in units" :key="unit" class="unit-chip">
          <span>{{ unit }}</span>
          <el-button link type="danger" :icon="Delete" @click="removeUnit(unit)" />
        </div>
      </div>
    </article>
  </div>
</template>
