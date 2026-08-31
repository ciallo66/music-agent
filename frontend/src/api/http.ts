import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { TokenResponse } from '../types/auth'

type RetriableRequest = InternalAxiosRequestConfig & { _retry?: boolean }

let readAccessToken: () => string | null = () => null
let saveAccessToken: (token: string | null) => void = () => undefined
let refreshRequest: Promise<string> | null = null

export const http = axios.create({ baseURL: '/api/v1', withCredentials: true, timeout: 10_000 })
const refreshClient = axios.create({ baseURL: '/api/v1', withCredentials: true, timeout: 10_000 })

export function configureAuthToken(
  reader: () => string | null,
  writer: (token: string | null) => void,
): void {
  readAccessToken = reader
  saveAccessToken = writer
}

export function getAccessToken(): string | null {
  return readAccessToken()
}

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
