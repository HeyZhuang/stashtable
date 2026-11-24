// API 请求层 —— TypeScript 迁移版本
// 统一 token 管理 + 请求封装（行为与原 JS 版完全一致，加类型声明）
import type { SatellitePosition, DashboardSummary, Observation, ApodData, ReplayPoint } from './types'

const TOKEN_KEY = 'satdash_token'
const LOCAL_TOKEN_KEY = 'satdash_local_token'
const USER_KEY = 'satdash_user'

export const getToken = (): string => localStorage.getItem(TOKEN_KEY) || ''
export const getLocalToken = (): string => localStorage.getItem(LOCAL_TOKEN_KEY) || ''
export const getUser = (): Record<string, string> => {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || '{}')
  } catch { return {} }
}

interface ApiBody {
  code?: string
  message?: string
  detail?: { message?: string }
  token?: string
  localToken?: string
  user?: Record<string, string>
  error?: string
  [key: string]: unknown
}

export async function api<T = ApiBody>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(options.headers as Record<string, string> | undefined) }
  // 优先用 LLMOps token，没有则用本地 token
  const token = getToken() || getLocalToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const response = await fetch(`/satdash${path}`, { ...options, headers })
  const body = (await response.json().catch(() => ({}))) as ApiBody
  if (!response.ok) {
    if (response.status === 401 && path !== '/api/auth/login') {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(LOCAL_TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      window.dispatchEvent(new Event('satdash-unauthorized'))
    }
    throw new Error(body?.detail?.message || body?.error || `请求失败 (${response.status})`)
  }
  return body as T
}

export async function login(email: string, password: string): Promise<ApiBody> {
  // 统一邮箱登录（内置 admin 已移除，仅支持 LLMOps 邮箱账号）
  const data = (await api<ApiBody>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }))

  // 保存双 token（token=API 鉴权，localToken=WebSocket 鉴权）
  if (data.token) localStorage.setItem(TOKEN_KEY, data.token)
  if (data.localToken) localStorage.setItem(LOCAL_TOKEN_KEY, data.localToken)
  if (data.user) localStorage.setItem(USER_KEY, JSON.stringify(data.user))

  return data
}

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(LOCAL_TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}
