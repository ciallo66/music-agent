// 个人画像缓存：进入页面立即用缓存渲染，后台静默刷新，避免每次重新加载。
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getMusicProfile } from '../api/profile'
import { showError } from '../utils/feedback'
import type { MusicProfileResponse } from '../types/profile'

export const useProfileStore = defineStore('profile', () => {
  /** 已拉取到的画像数据；null 表示从未成功加载过。 */
  const profile = ref<MusicProfileResponse | null>(null)
  /** 首次加载（页面还没有任何数据可展示）。 */
  const loading = ref(false)
  /** 后台刷新（页面已有数据，只是在更新）。 */
  const refreshing = ref(false)
  const errorMessage = ref('')
  const loadedOnce = ref(false)

  /**
   * 拉取画像。
   * @param force - 为 true 时即使有缓存也重新拉取（点「刷新数据」用）。
   */
  async function fetchProfile(force = false): Promise<void> {
    if (loading.value || refreshing.value) return
    if (loadedOnce.value && !force) return

    if (profile.value === null) loading.value = true
    else refreshing.value = true
    errorMessage.value = ''
    try {
      const { data } = await getMusicProfile()
      profile.value = data
      loadedOnce.value = true
    } catch (error) {
      errorMessage.value = '暂时无法读取画像数据，请稍后重试。'
      // 已有缓存时不要再弹错误打断阅读，只保留页面上的提示。
      if (profile.value === null) showError(error, '个人画像加载失败')
    } finally {
      loading.value = false
      refreshing.value = false
    }
  }

  /** 退出登录或切换账号时清空缓存，避免看到别人的画像。 */
  function clear(): void {
    profile.value = null
    loadedOnce.value = false
    errorMessage.value = ''
  }

  return { profile, loading, refreshing, errorMessage, loadedOnce, fetchProfile, clear }
})
