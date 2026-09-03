// 个性化推荐接口。
import { http } from './http'
import type { RecommendationPage } from '../types/music'

// 获取推荐歌曲；后端负责选择个性化或热门兜底策略。
export function listRecommendations(limit = 8) {
  return http.get<RecommendationPage>('/recommendations', { params: { limit } })
}
