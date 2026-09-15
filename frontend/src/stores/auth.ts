// 管理登录态、用户资料及 Token 生命周期。
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { configureAuthToken, http, refreshAccessToken } from '../api/http'
import type { TokenResponse, UserProfile } from '../types/auth'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const user = ref<UserProfile | null>(null)
  const initialized = ref(false)
  let initializationRequest: Promise<void> | null = null
  const isAuthenticated = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'admin')

  configureAuthToken(
    () => accessToken.value,
    (token) => {
      accessToken.value = token
      if (token === null) user.value = null
    },
  )

  // 根据登录入口读取用户资料，管理员入口使用独立接口。
  async function fetchProfile(admin = false): Promise<void> {
    const endpoint = admin ? '/admin/auth/me' : '/auth/me'
    const { data } = await http.get<UserProfile>(endpoint)
    user.value = data
  }

  // 登录并保存 Access Token；资料读取失败时回滚登录状态。
  async function login(username: string, password: string, admin = false): Promise<void> {
    const endpoint = admin ? '/admin/auth/login' : '/auth/login'
    const { data } = await http.post<TokenResponse>(endpoint, { username, password })
    accessToken.value = data.access_token
    await fetchProfile(admin)
  }

  // 注册普通用户并返回后端创建的资料。
  async function register(username: string, password: string): Promise<UserProfile> {
    const { data } = await http.post<UserProfile>('/auth/register', { username, password })
    return data
  }

  // 通知后端撤销 Refresh Token，并清理本地用户和 Token。
  async function logout(): Promise<void> {
    try {
      await http.post('/auth/logout')
    } finally {
      accessToken.value = null
      user.value = null
    }
  }

  // 应用启动时尝试恢复会话；失败只代表未登录，不阻断应用启动。
  async function initialize(): Promise<void> {
    if (initialized.value) return
    if (initializationRequest !== null) return initializationRequest

    initializationRequest = (async () => {
      try {
        await refreshAccessToken()
        await fetchProfile()
      } catch {
        accessToken.value = null
        user.value = null
      } finally {
        initialized.value = true
        initializationRequest = null
      }
    })()

    return initializationRequest
  }

  return {
    initialized,
    isAdmin,
    isAuthenticated,
    user,
    initialize,
    login,
    logout,
    register,
  }
})
