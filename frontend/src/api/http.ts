// Axios 实例、Token 注入及 401 刷新机制。
import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { TokenResponse } from '../types/auth'

type RetriableRequest = InternalAxiosRequestConfig & { _retry?: boolean }

let readAccessToken: () => string | null = () => null
let saveAccessToken: (token: string | null) => void = () => undefined
let refreshRequest: Promise<string> | null = null

// 所有请求共用同一个刷新 Promise，避免多个并发 401 同时轮换 Refresh Token。

export const http = axios.create({ baseURL: '/api/v1', withCredentials: true, timeout: 10_000 })
const refreshClient = axios.create({ baseURL: '/api/v1', withCredentials: true, timeout: 10_000 })

// 注入认证状态读写器，隔离网络层与 Pinia。
export function configureAuthToken(
  reader: () => string | null,
  writer: (token: string | null) => void,
): void {
  // 由 auth store 注入读写函数，API 层因此不依赖具体状态管理实现。
  readAccessToken = reader
  saveAccessToken = writer
}

// 读取当前 Access Token，供原生 fetch 使用。
export function getAccessToken(): string | null {
  // SSE fetch 不能复用 Axios 拦截器，因此暴露当前 Access Token。
  return readAccessToken()
}

// 单飞刷新 Token；并发请求共享同一次刷新结果。
export async function refreshAccessToken(): Promise<string> {
  if (refreshRequest === null) {
    refreshRequest = refreshClient
      .post<TokenResponse>('/auth/refresh')
      .then(({ data }) => {
        saveAccessToken(data.access_token)
        return data.access_token
      })
      .finally(() => {
        refreshRequest = null
      })
  }
  return refreshRequest
}

http.interceptors.request.use((config) => {
  const token = readAccessToken()
  if (token !== null) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(undefined, async (error: AxiosError) => {
  const request = error.config as RetriableRequest | undefined
  const isAuthEntry =
    request?.url?.includes('/auth/login') === true ||
    request?.url?.includes('/auth/register') === true ||
    request?.url?.includes('/auth/refresh') === true

  if (error.response?.status !== 401 || request === undefined || request._retry || isAuthEntry) {
    return Promise.reject(error)
  }

  request._retry = true
  try {
    const token = await refreshAccessToken()
    request.headers.Authorization = `Bearer ${token}`
    return await http(request)
  } catch (refreshError) {
    saveAccessToken(null)
    return Promise.reject(refreshError)
  }
})
