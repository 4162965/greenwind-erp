import axios from 'axios'

function getApiBaseUrl() {
  const envBase = import.meta.env.VITE_API_BASE_URL
  if (envBase) return envBase
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

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('greenwind_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
      localStorage.removeItem('greenwind_token')
      localStorage.removeItem('greenwind_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)
