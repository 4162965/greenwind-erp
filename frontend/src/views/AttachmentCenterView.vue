<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ArrowDown, Delete, Download, Plus, Refresh, Search, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

type Row = Record<string, any>

const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const targetType = ref('')
const rows = ref<Row[]>([])
const dialogVisible = ref(false)
const fileInput = ref<HTMLInputElement>()
const form = reactive<Row>({
  target_type: '椤圭洰璧勬枡',
  target_id: null,
  target_name: '',
  file_name: '',
  file_type: '',
  file_size: 0,
  data_url: '',
  notes: '',
})

const targetOptions = ['椤圭洰璧勬枡', '鍚堝悓璧勬枡', '璁㈠崟璧勬枡', '鍏绘姢鐓х墖', '閲囪喘璧勬枡', '杞﹁締璧勬枡', '璐㈠姟璧勬枡', '鍏朵粬璧勬枡']

function sizeText(size: number) {
  if (!size) return '-'
  if (size < 1024) return `${size}B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)}KB`
  return `${(size / 1024 / 1024).toFixed(2)}MB`
}

function resetForm() {
  Object.assign(form, {
    target_type: '椤圭洰璧勬枡',
    target_id: null,
    target_name: '',
    file_name: '',
    file_type: '',
    file_size: 0,
    data_url: '',
    notes: '',
  })
  if (fileInput.value) fileInput.value.value = ''
}

async function loadData() {
  loading.value = true
  try {
    const response = await api.get('/attachments', {
      params: { keyword: keyword.value.trim(), target_type: targetType.value },
    })
    rows.value = response.data.items || []
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '闄勪欢鍒楄〃鍔犺浇澶辫触')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function chooseFile() {
  fileInput.value?.click()
}

function handleFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (file.size > 8 * 1024 * 1024) {
    ElMessage.warning('鍗曚釜闄勪欢涓嶈兘瓒呰繃8MB')
    input.value = ''
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    form.file_name = file.name
    form.file_type = file.type || 'application/octet-stream'
    form.file_size = file.size
    form.data_url = String(reader.result)
  }
  reader.readAsDataURL(file)
}

async function saveAttachment() {
  if (!form.file_name || !form.data_url) {
    ElMessage.warning('璇峰厛閫夋嫨闄勪欢鏂囦欢')
    return
  }
  saving.value = true
  try {
    await api.post('/attachments', form)
    ElMessage.success('闄勪欢宸蹭繚瀛?)
    dialogVisible.value = false
    await loadData()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '闄勪欢淇濆瓨澶辫触')
  } finally {
    saving.value = false
  }
}

function download(row: Row) {
  const link = document.createElement('a')
  link.href = row.data_url
  link.download = row.file_name || '闄勪欢'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

async function remove(row: Row) {
  await ElMessageBox.confirm(`纭畾鍒犻櫎闄勪欢鈥?{row.file_name}鈥濆悧锛焋, '鍒犻櫎纭', { type: 'warning' })
  await api.delete(`/attachments/${row.id}`)
  ElMessage.success('闄勪欢宸插垹闄?)
  await loadData()
}

onMounted(loadData)
</script>

<template>
  <div class="page attachment-page">
    <div class="page-heading compact attachment-hero">
      <div>
        <p class="eyebrow">DOCUMENTS</p>
        <h1>璧勬枡闄勪欢涓績</h1>
        <p>鍏堢粺涓€淇濆瓨鍚堝悓銆佽鍗曘€侀」鐩€佸吇鎶ょ収鐗囩瓑璧勬枡锛屽悗闈㈠啀閫愭鍏宠仈鍒板悇涓笟鍔¤鎯呴〉銆?/p>
      </div>
      <el-button type="success" :icon="Plus" @click="openCreate">涓婁紶闄勪欢</el-button>
    </div>

    <article class="panel table-panel">
      <div class="table-toolbar">
        <el-select v-model="targetType" clearable placeholder="璧勬枡绫诲瀷" style="width:150px" @change="loadData">
          <el-option v-for="item in targetOptions" :key="item" :label="item" :value="item" />
        </el-select>
        <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="鎼滅储绫诲瀷銆佸叧鑱斿悕绉般€佹枃浠跺悕銆佸娉? @keyup.enter="loadData" @clear="loadData" />
        <el-button type="success" plain :icon="Search" @click="loadData">鏌ヨ</el-button>
        <el-button :icon="Refresh" @click="keyword=''; targetType=''; loadData()">閲嶇疆</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="target_type" label="璧勬枡绫诲瀷" width="110" />
        <el-table-column prop="target_name" label="鍏宠仈鍚嶇О" min-width="170" show-overflow-tooltip />
        <el-table-column prop="file_name" label="鏂囦欢鍚? min-width="220" show-overflow-tooltip />
        <el-table-column prop="file_type" label="鏂囦欢绫诲瀷" min-width="150" show-overflow-tooltip />
        <el-table-column label="澶у皬" width="95"><template #default="scope">{{ sizeText(scope.row.file_size) }}</template></el-table-column>
        <el-table-column prop="uploader_name" label="涓婁紶浜? width="110" />
        <el-table-column prop="created_at" label="涓婁紶鏃堕棿" width="170" />
        <el-table-column prop="notes" label="澶囨敞" min-width="180" show-overflow-tooltip />
        <el-table-column label="鎿嶄綔" width="95">
          <template #default="scope">
            <el-dropdown trigger="click">
              <el-button link type="primary" class="table-more-button">鏇村<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="download(scope.row)">涓嬭浇</el-dropdown-item>
                  <el-dropdown-item divided @click="remove(scope.row)">鍒犻櫎</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <el-dialog v-model="dialogVisible" title="涓婁紶闄勪欢" width="680px" destroy-on-close>
      <el-form label-position="top">
        <div class="form-grid two">
          <el-form-item label="璧勬枡绫诲瀷">
            <el-select v-model="form.target_type" style="width:100%">
              <el-option v-for="item in targetOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="鍏宠仈ID/缂栧彿">
            <el-input-number v-model="form.target_id" :min="0" controls-position="right" style="width:100%" />
          </el-form-item>
          <el-form-item label="鍏宠仈鍚嶇О" class="wide">
            <el-input v-model="form.target_name" placeholder="渚嬪锛氶噾铻嶄腑蹇冪鎽嗗悎鍚屻€佹崲鑺卞崟 HH-001銆?妤兼€荤粡鐞嗗姙鍏" />
          </el-form-item>
          <el-form-item label="澶囨敞" class="wide">
            <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="渚嬪锛氬悎鍚屾壂鎻忎欢銆佺幇鍦烘洿鎹㈠墠鐓х墖銆佸彂绁ㄩ檮浠剁瓑" />
          </el-form-item>
        </div>

        <div class="upload-box" @click="chooseFile">
          <input ref="fileInput" type="file" class="hidden-input" @change="handleFile" />
          <el-icon><UploadFilled /></el-icon>
          <strong>{{ form.file_name || '鐐瑰嚮閫夋嫨鏂囦欢' }}</strong>
          <span>{{ form.file_name ? `${sizeText(form.file_size)} 路 ${form.file_type || '鏈煡绫诲瀷'}` : '鏀寔鍥剧墖銆丳DF銆乄ord銆丒xcel 绛夊父鐢ㄨ祫鏂欙紝鍗曚釜涓嶈秴杩?MB' }}</span>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">鍙栨秷</el-button>
        <el-button type="success" :loading="saving" @click="saveAttachment">淇濆瓨闄勪欢</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.attachment-hero {
  background:
    radial-gradient(circle at 80% 20%, rgba(56, 189, 248, .18), transparent 25%),
    linear-gradient(135deg, #f0f9ff 0%, #f7fee7 100%);
}

.upload-box {
  min-height: 150px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px dashed #9acbb0;
  border-radius: 18px;
  color: #0f766e;
  background: #f8fffb;
  cursor: pointer;
}

.upload-box .el-icon {
  font-size: 38px;
}

.upload-box span {
  color: #64748b;
  font-size: 12px;
}
</style>

