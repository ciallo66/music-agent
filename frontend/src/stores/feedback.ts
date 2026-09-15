// 推荐反馈状态管理：反馈动作列表、当前用户反馈记录与汇总统计。
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { FeedbackActionItem, FeedbackStats } from '../types/music'
import { createFeedback, getFeedbackStats, listFeedbackActions } from '../api/feedback'
import { ElMessage } from 'element-plus'

export const useFeedbackStore = defineStore('feedback', () => {
  const actions = ref<FeedbackActionItem[]>([])
  const stats = ref<FeedbackStats | null>(null)
  const submitted = ref(new Set<number>())

  const loaded = computed(() => actions.value.length > 0)

  async function loadActions() {
    if (loaded.value) return
    try {
      const { data } = await listFeedbackActions()
      actions.value = data
    } catch {
      ElMessage.error('加载反馈选项失败')
    }
  }

  async function loadStats() {
    try {
      const { data } = await getFeedbackStats()
      stats.value = data
    } catch {
      // 游客不展示统计
    }
  }

  async function submitFeedback(songId: number, action: string) {
    if (!actions.value.find((a) => a.action === action)) return
    if (submitted.value.has(songId)) return
    submitted.value.add(songId)
    try {
      await createFeedback(songId, action)
      await loadStats()
      ElMessage.success(`已记录你的"${action}"反馈`)
    } catch {
      ElMessage.error('记录反馈失败')
    } finally {
      submitted.value.delete(songId)
    }
  }

  return {
    actions,
    stats,
    loaded,
    loadActions,
    loadStats,
    submitted,
    submitFeedback,
  }
})
