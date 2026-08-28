import { http } from './http'
import type { RecommendationPage } from '../types/music'

export function listRecommendations(limit = 8) {
  return http.get<RecommendationPage>('/recommendations', { params: { limit } })
}
