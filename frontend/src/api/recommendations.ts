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

// 记录一次收听：后端的画像聚合与「最近播放」直接读这张表，没有它行为数据永远长不起来。
// 演示账号只读，后端会返回 403，由调用方按提示处理。
export function recordPlay(songId: number) {
  return http.post<void>('/plays', { song_id: songId })
}
