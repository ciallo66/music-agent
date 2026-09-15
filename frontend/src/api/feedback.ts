// 推荐反馈接口。
import { http } from './http'
import type {
  FeedbackActionItem,
  FeedbackStats,
  RecommendationFeedbackResponse,
} from '../types/music'

export type {
  FeedbackActionItem,
  FeedbackStats,
  RecommendationFeedbackResponse,
} from '../types/music'

/** 获取可用反馈类型。 */
export function listFeedbackActions() {
  return http.get<FeedbackActionItem[]>('/feedback/actions')
}

/** 提交反馈。 */
export function createFeedback(songId: number, action: string) {
  return http.post<RecommendationFeedbackResponse>('/feedback', { song_id: songId, action })
}

/** 删除反馈。 */
export function removeFeedback(songId: number) {
  return http.delete(`/feedback/${songId}`)
}

/** 获取当前用户的反馈统计。 */
export function getFeedbackStats() {
  return http.get<FeedbackStats>('/feedback/stats')
}
