import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api/client'

export type AuthScope = 'desktop' | 'mobile'

export interface UserInfo {
  id: number
  username: string
  display_name: string
  role: string
  module_permissions: string[]
  product_category_permissions: string[]
}

export const useAuthStore = defineStore('auth', () => {
  const initialScope: AuthScope = window.location.pathname.startsWith('/mobile') ? 'mobile' : 'desktop'
  const activeScope = ref<AuthScope>(initialScope)
  const token = ref('')
  const user = ref<UserInfo | null>(null)
  const isLoggedIn = computed(() => Boolean(token.value))

  function storageKeys(scope: AuthScope) {
    return scope === 'mobile'
      ? { token: 'greenwind_mobile_token', user: 'greenwind_mobile_user' }
      : { token: 'greenwind_token', user: 'greenwind_user' }
  }

  function readUser(key: string) {
    try {
      const saved = localStorage.getItem(key)
      return saved ? JSON.parse(saved) as UserInfo : null
    } catch {
      localStorage.removeItem(key)
      return null
    }
  }

  function activateScope(scope: AuthScope) {
    activeScope.value = scope
    const keys = storageKeys(scope)
    token.value = localStorage.getItem(keys.token) || ''
    user.value = readUser(keys.user)
  }

  async function login(username: string, password: string, scope: AuthScope = activeScope.value) {
    activateScope(scope)
    const { data } = await api.post('/auth/login', { username, password })
    token.value = data.access_token
    user.value = data.user
    const keys = storageKeys(scope)
    localStorage.setItem(keys.token, token.value)
    localStorage.setItem(keys.user, JSON.stringify(user.value))
  }

  async function changePassword(oldPassword: string, newPassword: string) {
    await api.post('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
  }

  function logout(scope: AuthScope = activeScope.value) {
    const keys = storageKeys(scope)
    localStorage.removeItem(keys.token)
    localStorage.removeItem(keys.user)
    if (scope === activeScope.value) {
      token.value = ''
      user.value = null
    }
  }

  activateScope(initialScope)

  return { activeScope, token, user, isLoggedIn, activateScope, login, changePassword, logout }
})
