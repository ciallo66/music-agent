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
  // 演示账号（用户名与后端 DEMO_USERNAME 默认值一致）：正常功能可用，仅后台改数据只读。
  const DEMO_USERNAME = 'demo'
  const isDemo = computed(() => user.value?.username.toLowerCase() === DEMO_USERNAME)
  // 能否改后台数据由服务端判定（admin 角色且不是演示账号），前端据此禁用入口。
  const canManageData = computed(() => user.value?.can_manage_data === true)

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
    // 换账号时先丢掉上一个账号的画像缓存，避免看到别人的数据
    const { useProfileStore } = await import('./profile')
    useProfileStore().clear()
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
      // 动态引入，避免模块循环依赖；清掉画像缓存防止换账号后看到上一个账号的数据
      const { useProfileStore } = await import('./profile')
      useProfileStore().clear()
    }
  }

  // 应用启动时尝试恢复会话；失败只代表未登录，不阻断应用启动。
  // 失败时把 initialized 复位：前台与后台是两个独立入口，跨入口是整页跳转，
  // 新文档启动后要能再恢复一次会话，否则会被守卫误判成未登录。
  async function initialize(): Promise<void> {
    if (initialized.value) return
    if (initializationRequest !== null) return initializationRequest

    initializationRequest = (async () => {
      try {
        await refreshAccessToken()
        await fetchProfile()
        initialized.value = true
      } catch {
        accessToken.value = null
        user.value = null
        initialized.value = false
      } finally {
        initializationRequest = null
      }
    })()

    return initializationRequest
  }

  return {
    initialized,
    isAdmin,
    isAuthenticated,
    isDemo,
    canManageData,
    user,
    initialize,
    login,
    logout,
    register,
  }
})
