// 推荐反馈状态管理：反馈动作列表、当前用户反馈记录与汇总统计。
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { FeedbackActionItem, FeedbackStats } from '../types/music'
import {
  createFeedback,
  getFeedbackStats,
  listFeedbackActions,
  removeFeedback,
} from '../api/feedback'
import { ElMessage } from 'element-plus'

export const useFeedbackStore = defineStore('feedback', () => {
  const actions = ref<FeedbackActionItem[]>([])
  const stats = ref<FeedbackStats | null>(null)
  const submitted = ref(new Set<number>())
  // 仅在成功加载后置为 true；空列表或未登录失败都保持可重试状态。
  const loaded = ref(false)

  async function loadActions() {
    if (loaded.value) return
    try {
      const { data } = await listFeedbackActions()
      actions.value = data
      loaded.value = true
    } catch {
      // 未登录时接口返回 401，保持静默；登录后页面会再次触发加载。
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

  /** 当前用户对某首歌已提交的反馈动作；没有则无该键。 */
  const mine = ref<Record<number, string>>({})

  /** 提交反馈；再次提交同一动作视为取消。返回是否处理成功。 */
  async function submitFeedback(songId: number, action: string): Promise<boolean> {
    if (!actions.value.find((a) => a.action === action)) return false
    if (submitted.value.has(songId)) return false
    submitted.value.add(songId)
    try {
      if (mine.value[songId] === action) {
        await removeFeedback(songId)
        const next = { ...mine.value }
        delete next[songId]
        mine.value = next
        ElMessage.success('已取消该反馈')
      } else {
        await createFeedback(songId, action)
        mine.value = { ...mine.value, [songId]: action }
        ElMessage.success('反馈已记录')
      }
      await loadStats()
      return true
    } catch {
      ElMessage.error('记录反馈失败')
      return false
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
    mine,
    submitFeedback,
  }
})
