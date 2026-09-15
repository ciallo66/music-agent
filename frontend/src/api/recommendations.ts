// 个性化推荐接口：普通列表与结构化卡片两种视图。
import { http } from './http'
import type { RecommendationPage, StructuredRecommendationCard } from '../types/music'

// 获取推荐歌曲；后端负责选择个性化或热门兜底策略。
export function listRecommendations(limit = 8) {
  return http.get<RecommendationPage>('/recommendations', { params: { limit } })
}

// 获取结构化推荐卡片；用于卡片式展示与反馈。
export function listRecommendationCards(limit = 8) {
  return http.get<StructuredRecommendationCard[]>('/recommendations/cards', {
    params: { limit },
  })
}
