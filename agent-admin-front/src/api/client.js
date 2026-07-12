import axios from 'axios'
import { ElMessage } from 'element-plus'

const TOKEN_KEY = 'admin_token'
const DEFAULT_TOKEN = 'admin-secret-2026'

const client = axios.create({
  baseURL: '/api/admin',
  timeout: 30000
})

client.interceptors.request.use(config => {
  const token = localStorage.getItem(TOKEN_KEY) || DEFAULT_TOKEN
  config.headers['X-Admin-Token'] = token
  return config
})

client.interceptors.response.use(
  response => response.data,
  error => {
    const msg = error.response?.data?.message || error.message || '请求失败'
    const status = error.response?.status
    if (status === 401) {
      ElMessage.error('认证失败，请检查 Token')
    } else if (status === 403) {
      ElMessage.error('无权限访问')
    } else {
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  }
)

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || DEFAULT_TOKEN
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export default client
