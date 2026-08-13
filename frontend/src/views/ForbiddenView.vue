<script setup lang="ts">
import { ArrowLeft, House } from '@element-plus/icons-vue'
</script>

<template>
  <div class="page forbidden-page">
    <article class="panel forbidden-card">
      <div class="forbidden-mark">403</div>
      <h1>没有访问权限</h1>
      <p>当前账号没有打开这个模块的权限。如果确实需要使用，请让管理员到“员工管理 → 编辑员工 → 模块权限”里勾选对应模块。</p>
      <div class="forbidden-actions">
        <el-button :icon="ArrowLeft" @click="$router.back()">返回上一页</el-button>
        <el-button type="success" :icon="House" @click="$router.push('/')">回到工作台</el-button>
      </div>
    </article>
  </div>
</template>
