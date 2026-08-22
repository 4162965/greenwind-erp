import axios from 'axios'

function getApiBaseUrl() {
  const envBase = String(import.meta.env.VITE_API_BASE_URL || '').trim()
  if (envBase) return envBase.replace(/\/$/, '')
  if (typeof window !== 'undefined') {
    const { protocol, hostname } = window.location
    return `${protocol}//${hostname}:8010/api/v1`
  }
  return '/api/v1'
}

export const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 15000,
})

function currentSession() {
  const mobile = window.location.pathname.startsWith('/mobile')
  return mobile
    ? { tokenKey: 'greenwind_mobile_token', userKey: 'greenwind_mobile_user', loginPath: '/mobile/login' }
    : { tokenKey: 'greenwind_token', userKey: 'greenwind_user', loginPath: '/login' }
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(currentSession().tokenKey)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
      const session = currentSession()
      localStorage.removeItem(session.tokenKey)
      localStorage.removeItem(session.userKey)
      window.location.href = session.loginPath
    }
    return Promise.reject(error)
  },
)
