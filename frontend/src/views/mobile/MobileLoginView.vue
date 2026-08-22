<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, Lock, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../../stores/auth'

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

async function submit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.username, form.password, 'mobile')
    ElMessage.success('登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    await router.replace(redirect.startsWith('/mobile') && redirect !== '/mobile/login' ? redirect : '/mobile')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '登录失败，请检查账号、密码或服务状态')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="mobile-login-page">
    <section class="mobile-login-shell">
      <div class="mobile-login-brand" aria-label="绿风环境花卉">
        <span>绿</span>
        <div><strong>绿风环境花卉</strong><small>员工移动工作台</small></div>
      </div>

      <div class="mobile-login-heading">
        <p>MOBILE ERP</p>
        <h1>手机端登录</h1>
        <span>登录后查看任务、报单、采购和仓库工作。</span>
      </div>

      <el-form :model="form" size="large" @submit.prevent="submit">
        <el-form-item>
          <el-input v-model="form.username" autocomplete="username" placeholder="账号或手机号" :prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            autocomplete="current-password"
            type="password"
            show-password
            placeholder="登录密码"
            :prefix-icon="Lock"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button class="mobile-login-submit" type="success" :loading="loading" @click="submit">
          进入移动工作台
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </el-form>

      <router-link class="desktop-login-link" to="/login">电脑端登录</router-link>
    </section>
  </main>
</template>

<style scoped>
.mobile-login-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: grid;
  place-items: center;
  padding: max(24px, env(safe-area-inset-top)) 20px max(24px, env(safe-area-inset-bottom));
  color: #17382a;
  background: linear-gradient(180deg, #e8f8f0 0%, #f5faf7 42%, #eef4f8 100%);
}
.mobile-login-shell { width: min(100%, 390px); }
.mobile-login-brand { display: flex; align-items: center; gap: 11px; }
.mobile-login-brand > span {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: #fff;
  background: #15935a;
  font-size: 18px;
  font-weight: 800;
  box-shadow: 0 8px 20px rgba(21, 147, 90, .18);
}
.mobile-login-brand div { display: flex; flex-direction: column; gap: 2px; }
.mobile-login-brand strong { font-size: 16px; }
.mobile-login-brand small { color: #789087; font-size: 11px; }
.mobile-login-heading { margin: 64px 0 28px; }
.mobile-login-heading p { margin: 0 0 8px; color: #15935a; font-size: 11px; font-weight: 800; }
.mobile-login-heading h1 { margin: 0; font-size: 28px; line-height: 1.25; letter-spacing: 0; }
.mobile-login-heading span { display: block; margin-top: 10px; color: #718179; font-size: 14px; line-height: 1.6; }
.mobile-login-page :deep(.el-form-item) { margin-bottom: 14px; }
.mobile-login-page :deep(.el-input__wrapper) {
  min-height: 50px;
  border-radius: 8px;
  box-shadow: 0 0 0 1px #dce7e1 inset;
}
.mobile-login-page :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 1px #15935a inset; }
.mobile-login-submit {
  --el-button-bg-color: #15935a;
  --el-button-border-color: #15935a;
  --el-button-hover-bg-color: #107a4a;
  --el-button-hover-border-color: #107a4a;
  width: 100%;
  height: 50px;
  margin-top: 6px;
  border-radius: 8px;
  font-weight: 700;
}
.mobile-login-submit :deep(.el-icon) { margin-left: 7px; }
.desktop-login-link {
  display: block;
  margin-top: 22px;
  color: #658076;
  font-size: 13px;
  text-align: center;
  text-decoration: none;
}
@media (max-height: 620px) {
  .mobile-login-heading { margin: 36px 0 22px; }
}
</style>
