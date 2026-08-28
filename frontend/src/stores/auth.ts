import axios from 'axios'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { configureAuthToken, http, refreshAccessToken } from '../api/http'
import type { TokenResponse } from '../types/music'

export interface UserProfile {
  id: number
  username: string
  role: 'user' | 'admin'
  status: 'active' | 'disabled'
  created_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const user = ref<UserProfile | null>(null)
  const initialized = ref(false)
  const isAuthenticated = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'admin')

  configureAuthToken(
    () => accessToken.value,
    (token) => {
      accessToken.value = token
      if (token === null) user.value = null
    },
  )

  async function fetchProfile(admin = false): Promise<void> {
    const endpoint = admin ? '/admin/auth/me' : '/auth/me'
    const { data } = await http.get<UserProfile>(endpoint)
    user.value = data
  }

  async function login(username: string, password: string, admin = false): Promise<void> {
    const endpoint = admin ? '/admin/auth/login' : '/auth/login'
    const { data } = await http.post<TokenResponse>(endpoint, { username, password })
    accessToken.value = data.access_token
    await fetchProfile(admin)
  }

  async function register(username: string, password: string): Promise<UserProfile> {
    const { data } = await http.post<UserProfile>('/auth/register', { username, password })
    return data
  }

  async function logout(): Promise<void> {
    try {
      await http.post('/auth/logout')
    } finally {
      accessToken.value = null
      user.value = null
    }
  }

  async function initialize(): Promise<void> {
    try {
      await refreshAccessToken()
      await fetchProfile()
    } catch {
      accessToken.value = null
      user.value = null
    } finally {
      initialized.value = true
    }
  }

  function errorMessage(error: unknown): string {
    if (axios.isAxiosError<{ detail?: string }>(error)) {
      return error.response?.data?.detail ?? '请求失败，请稍后重试'
    }
    return '发生未知错误，请稍后重试'
  }

  return {
    initialized,
    isAdmin,
    isAuthenticated,
    user,
    errorMessage,
    initialize,
    login,
    logout,
    register,
  }
})
