import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api/client'

export interface UserInfo {
  id: number
  username: string
  display_name: string
  role: string
  module_permissions: string[]
  product_category_permissions: string[]
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('greenwind_token') || '')
  const saved = localStorage.getItem('greenwind_user')
  const user = ref<UserInfo | null>(saved ? JSON.parse(saved) : null)
  const isLoggedIn = computed(() => Boolean(token.value))

  async function login(username: string, password: string) {
    const { data } = await api.post('/auth/login', { username, password })
    token.value = data.access_token
    user.value = data.user
    localStorage.setItem('greenwind_token', token.value)
    localStorage.setItem('greenwind_user', JSON.stringify(user.value))
  }

  async function changePassword(oldPassword: string, newPassword: string) {
    await api.post('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('greenwind_token')
    localStorage.removeItem('greenwind_user')
  }

  return { token, user, isLoggedIn, login, changePassword, logout }
})
