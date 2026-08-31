import { http } from './http'
import type { FavoritePage } from '../types/library'
export type { FavoriteItem } from '../types/library'

export function listFavorites() {
  return http.get<FavoritePage>('/favorites')
}

export function addFavorite(songId: number) {
  return http.post<{ id: number }>('/favorites', { song_id: songId })
}

export function removeFavorite(songId: number) {
  return http.delete(`/favorites/${songId}`)
}
