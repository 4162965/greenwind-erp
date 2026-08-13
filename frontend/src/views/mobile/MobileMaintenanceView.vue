<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Delete, Plus, Refresh, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../../api/client'

type Row = Record<string, any>

const loading = ref(false)
const saving = ref(false)
const photoInput = ref<HTMLInputElement>()
const projects = ref<Row[]>([])
const plans = ref<Row[]>([])
const records = ref<Row[]>([])
const photos = ref<Row[]>([])
const form = reactive<Row>({
  plan_id: null,
  project_id: null,
  maintainer_id: null,
  service_date: new Date().toISOString().slice(0, 10),
  area_description: '',
  work_content: '浇水、修剪、清理黄叶、检查植物状态',
  site_issue: '',
  handle_result: '',
  customer_feedback: '',
  next_plan_date: '',
  status: '已完成',
  notes: '',
})

async function loadData() {
  loading.value = true
  try {
    const [projectRes, planRes, recordRes] = await Promise.all([
      api.get('/projects'),
      api.get('/maintenance/plans'),
      api.get('/maintenance/records'),
    ])
    projects.value = projectRes.data.items || []
    plans.value = planRes.data.items || []
    records.value = recordRes.data.items || []
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '养护数据加载失败')
  } finally {
    loading.value = false
  }
}

function selectPlan() {
  const plan = plans.value.find((item) => item.id === form.plan_id)
  if (!plan) return
  form.project_id = plan.project_id
  form.maintainer_id = plan.maintainer_id
  form.area_description = plan.area_description || ''
  form.work_content = plan.service_content || form.work_content
}

function choosePhotos() {
  photoInput.value?.click()
}

function handlePhotos(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (photos.value.length + files.length > 9) {
    ElMessage.warning('一次最多上传9张现场照片')
    input.value = ''
    return
  }
  files.forEach((file) => {
    if (file.size > 5 * 1024 * 1024) {
      ElMessage.warning(`${file.name}超过5MB，请压缩后上传`)
      return
    }
    const reader = new FileReader()
    reader.onload = () => photos.value.push({ file_name: file.name, file_type: file.type || 'image/*', file_size: file.size, data_url: String(reader.result) })
    reader.readAsDataURL(file)
  })
  input.value = ''
}

async function saveRecord() {
  if (!form.project_id && !form.plan_id) {
    ElMessage.warning('请选择项目或养护计划')
    return
  }
  saving.value = true
  try {
    form.photos = photos.value.map((item) => item.file_name).join('，')
    const response = await api.post('/maintenance/records', form)
    const record = response.data
    for (const photo of photos.value) {
      await api.post('/attachments', {
        target_type: '养护照片',
        target_id: record.id,
        target_name: `${record.record_no}｜${record.project_name || ''}`,
        file_name: photo.file_name,
        file_type: photo.file_type,
        file_size: photo.file_size,
        data_url: photo.data_url,
        notes: form.area_description || '',
      })
    }
    ElMessage.success(photos.value.length ? `已保存养护记录和${photos.value.length}张照片` : '养护记录已保存')
    photos.value = []
    form.site_issue = ''
    form.handle_result = ''
    form.customer_feedback = ''
    await loadData()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '养护记录保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="mobile-page" v-loading="loading">
    <section class="mobile-title">
      <div><p>MAINTENANCE</p><h1>写养护记录</h1></div>
      <button type="button" @click="loadData"><el-icon><Refresh /></el-icon></button>
    </section>

    <section class="mobile-form-card">
      <el-form label-position="top">
        <el-form-item label="关联养护计划">
          <el-select v-model="form.plan_id" clearable filterable placeholder="可选" @change="selectPlan">
            <el-option v-for="plan in plans" :key="plan.id" :label="`${plan.project_name}｜${plan.area_description || '全部区域'}`" :value="plan.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目" required>
          <el-select v-model="form.project_id" clearable filterable placeholder="请选择项目">
            <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="养护日期">
          <el-date-picker v-model="form.service_date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="区域/位置">
          <el-input v-model="form.area_description" placeholder="例如：A栋8楼总经理办公室" />
        </el-form-item>
        <el-form-item label="工作内容">
          <el-input v-model="form.work_content" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="现场问题">
          <el-input v-model="form.site_issue" type="textarea" :rows="3" placeholder="例如：绿萝状态差、花盆破损、需要换花" />
        </el-form-item>
        <el-form-item label="处理结果/建议">
          <el-input v-model="form.handle_result" type="textarea" :rows="3" placeholder="例如：已修剪，建议下次更换5盆绿萝" />
        </el-form-item>
        <el-form-item label="现场照片">
          <div class="mobile-photo-grid">
            <input ref="photoInput" class="hidden-input" type="file" accept="image/*" multiple @change="handlePhotos" />
            <button type="button" class="mobile-photo-add" @click="choosePhotos"><el-icon><UploadFilled /></el-icon><span>上传照片</span></button>
            <div v-for="(photo,index) in photos" :key="`${photo.file_name}-${index}`" class="mobile-photo">
              <el-image :src="photo.data_url" fit="cover" />
              <button type="button" @click="photos.splice(index,1)"><el-icon><Delete /></el-icon></button>
            </div>
          </div>
        </el-form-item>
        <el-button class="mobile-submit" type="success" :loading="saving" :icon="Plus" @click="saveRecord">保存养护记录</el-button>
      </el-form>
    </section>

    <section class="mobile-card">
      <div class="mobile-section-title"><strong>最近记录</strong></div>
      <div class="mobile-list">
        <article v-for="row in records.slice(0, 5)" :key="row.id">
          <strong>{{ row.project_name }}</strong>
          <span>{{ row.service_date }}｜{{ row.area_description || '全部区域' }}</span>
          <small>{{ row.site_issue || row.handle_result || '无现场问题' }}</small>
        </article>
      </div>
    </section>
  </div>
</template>
