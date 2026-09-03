// 用户收藏的查询、添加和删除接口。
import { http } from './http'
import type { FavoritePage } from '../types/library'
export type { FavoriteItem } from '../types/library'

// 查询当前用户的收藏 ID 列表。
export function listFavorites() {
  return http.get<FavoritePage>('/favorites')
}

// 收藏一首歌曲。
export function addFavorite(songId: number) {
  return http.post<{ id: number }>('/favorites', { song_id: songId })
}

// 取消收藏一首歌曲。
export function removeFavorite(songId: number) {
  return http.delete(`/favorites/${songId}`)
}
