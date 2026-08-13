<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Calendar, House, MagicStick, SwitchButton, Tickets } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const passwordDialogVisible = ref(false)
const passwordSaving = ref(false)
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const tabs = [
  { label: '首页', path: '/mobile', icon: House },
  { label: '任务', path: '/mobile/tasks', icon: Calendar },
  { label: '报单', path: '/mobile/exchange', icon: MagicStick },
  { label: '养护', path: '/mobile/maintenance', icon: Tickets },
]

const activePath = computed(() => route.path)
const displayName = computed(() => auth.user?.display_name || '绿风员工')

function go(path: string) {
  router.push(path)
}

function logout() {
  auth.logout()
  router.push('/login')
}

function resetPasswordForm() {
  passwordForm.oldPassword = ''
  passwordForm.newPassword = ''
  passwordForm.confirmPassword = ''
}

async function savePassword() {
  if (!passwordForm.oldPassword || !passwordForm.newPassword) {
    ElMessage.warning('请填写原密码和新密码')
    return
  }
  if (passwordForm.newPassword.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  passwordSaving.value = true
  try {
    await auth.changePassword(passwordForm.oldPassword, passwordForm.newPassword)
    ElMessage.success('密码修改成功')
    passwordDialogVisible.value = false
    resetPasswordForm()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '密码修改失败')
  } finally {
    passwordSaving.value = false
  }
}
</script>

<template>
  <div class="mobile-app">
    <header class="mobile-top">
      <div>
        <span>绿风移动端</span>
        <strong>{{ displayName }}</strong>
      </div>
      <div class="mobile-top-actions">
        <button type="button" @click="passwordDialogVisible = true">改密</button>
        <button type="button" @click="logout"><el-icon><SwitchButton /></el-icon></button>
      </div>
    </header>

    <main class="mobile-content">
      <router-view />
    </main>

    <nav class="mobile-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.path"
        type="button"
        :class="{ active: activePath === tab.path }"
        @click="go(tab.path)"
      >
        <el-icon><component :is="tab.icon" /></el-icon>
        <span>{{ tab.label }}</span>
      </button>
    </nav>

    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="92%" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="原密码" required>
          <el-input v-model="passwordForm.oldPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="passwordForm.newPassword" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="确认新密码" required>
          <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="passwordSaving" @click="savePassword">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
