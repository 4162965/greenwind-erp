<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Lock, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const form = reactive({ username: 'admin', password: 'admin123' })
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()

async function submit() {
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('欢迎回来')
    router.push('/')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '登录失败，请检查服务是否启动')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-visual">
      <div class="visual-content"><div class="visual-badge">绿风环境花卉</div><h1>管理软件</h1><p>订单、项目、采购、仓库、配送、合同和财务统一管理。</p><div class="visual-stats"><div><strong>ERP</strong><span>业务系统</span></div><div><strong>本地</strong><span>测试环境</span></div></div></div>
    </div>
    <div class="login-panel">
      <div class="login-card">
        <div class="mobile-brand"><span>绿</span>绿风环境</div>
        <p class="eyebrow">LOGIN</p><h2>系统登录</h2><p class="login-hint">请输入账号密码进入绿风管理软件。</p>
        <el-form :model="form" size="large" @submit.prevent="submit">
          <el-form-item><el-input v-model="form.username" placeholder="账号" :prefix-icon="User" /></el-form-item>
          <el-form-item><el-input v-model="form.password" type="password" show-password placeholder="密码" :prefix-icon="Lock" @keyup.enter="submit" /></el-form-item>
          <div class="login-options"><el-checkbox>保持登录</el-checkbox><a href="#">忘记密码？</a></div>
          <el-button class="login-button" type="primary" :loading="loading" @click="submit">进入系统</el-button>
        </el-form>
        <p class="dev-note">本地开发账号：admin / admin123</p>
      </div>
    </div>
  </div>
</template>
