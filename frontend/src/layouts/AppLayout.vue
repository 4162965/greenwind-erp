<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, Expand, Fold, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { menuItems, type MenuItem } from '../config/menu'
import { useAuthStore } from '../stores/auth'

const collapsed = ref(false)
const mobileMenuOpen = ref(false)
const passwordDialogVisible = ref(false)
const passwordSaving = ref(false)
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const activePath = computed(() => route.path)
const fullRoles = ['admin', '管理员', '经理', '老板']
const userRoles = computed(() => String(auth.user?.role || '').replace('，', ',').split(',').map((item) => item.trim()).filter(Boolean))
const hasFullAccess = computed(() => userRoles.value.some((role) => fullRoles.includes(role)))
const permissionSet = computed(() => new Set(auth.user?.module_permissions || []))
const visibleMenuItems = computed(() => menuItems.map(filterMenuItem).filter(Boolean) as MenuItem[])
const roleText = computed(() => auth.user?.role || '管理员')

function canSee(item: MenuItem) {
  if (hasFullAccess.value) return true
  const permissions = permissionSet.value
  if (!permissions.size) return true
  return !item.permission || permissions.has(item.permission)
}

function filterMenuItem(item: MenuItem): MenuItem | null {
  if (!canSee(item)) return null
  if (!item.children) return item
  const children = item.children.filter(canSee)
  return children.length ? { ...item, children } : null
}

function resetPasswordForm() {
  passwordForm.oldPassword = ''
  passwordForm.newPassword = ''
  passwordForm.confirmPassword = ''
}

function openPasswordDialog() {
  resetPasswordForm()
  passwordDialogVisible.value = true
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
    ElMessage.success('密码修改成功，请使用新密码登录')
    passwordDialogVisible.value = false
    resetPasswordForm()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '密码修改失败')
  } finally {
    passwordSaving.value = false
  }
}

function signOut() {
  auth.logout()
  router.push('/login')
}

function toggleMenu() {
  if (window.matchMedia('(max-width: 768px)').matches) {
    mobileMenuOpen.value = !mobileMenuOpen.value
  } else {
    collapsed.value = !collapsed.value
  }
}

watch(() => route.path, () => {
  mobileMenuOpen.value = false
})
</script>

<template>
  <div class="shell" :class="{ 'mobile-menu-open': mobileMenuOpen }">
    <div class="mobile-mask" @click="mobileMenuOpen = false"></div>
    <aside class="sidebar" :class="{ collapsed }">
      <div class="brand">
        <div class="brand-mark">绿</div>
        <div v-if="!collapsed" class="brand-copy"><strong>绿风环境</strong><span>花卉 ERP</span></div>
      </div>
      <el-scrollbar class="menu-scroll">
        <el-menu :default-active="activePath" router :collapse="collapsed" :collapse-transition="false">
          <template v-for="(item, index) in visibleMenuItems" :key="item.label">
            <el-sub-menu v-if="item.children" :index="`group-${index}`">
              <template #title><el-icon><component :is="item.icon" /></el-icon><span>{{ item.label }}</span></template>
              <el-menu-item v-for="child in item.children" :key="child.path" :index="child.path!">{{ child.label }}</el-menu-item>
            </el-sub-menu>
            <el-menu-item v-else :index="item.path!">
              <el-icon><component :is="item.icon" /></el-icon><template #title>{{ item.label }}</template>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>
      <div v-if="!collapsed" class="sidebar-foot"><span class="status-dot"></span>系统运行正常</div>
    </aside>

    <main class="workspace">
      <header class="topbar">
        <button class="icon-button" @click="toggleMenu"><el-icon><Expand v-if="collapsed" /><Fold v-else /></el-icon></button>
        <div class="topbar-title">
          <strong>绿风环境花卉 ERP</strong>
          <span>本地测试版</span>
        </div>
        <div class="search-box"><el-icon><Search /></el-icon><input placeholder="搜索客户、订单、商品" /></div>
        <div class="top-actions">
          <el-dropdown trigger="click">
            <div class="profile">
              <div class="avatar">{{ (auth.user?.display_name || '管').slice(0, 1) }}</div>
              <div class="profile-copy"><strong>{{ auth.user?.display_name || '系统管理员' }}</strong><span>{{ roleText }}</span></div>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="openPasswordDialog">修改密码</el-dropdown-item>
                <el-dropdown-item divided @click="signOut">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <section class="content"><router-view /></section>
    </main>

    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="420px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="原密码" required>
          <el-input v-model="passwordForm.oldPassword" type="password" show-password placeholder="请输入当前密码" />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="passwordForm.newPassword" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="确认新密码" required>
          <el-input v-model="passwordForm.confirmPassword" type="password" show-password placeholder="再输入一次新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="passwordSaving" @click="savePassword">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
