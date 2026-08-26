import { http } from './http'

export interface FavoriteItem {
  id: number
  song_id: number
  created_at: string
}

export function listFavorites() {
  return http.get<{ items: FavoriteItem[] }>('/favorites')
}

export function addFavorite(songId: number) {
  return http.post<{ id: number }>('/favorites', { song_id: songId })
}

export function removeFavorite(songId: number) {
  return http.delete(`/favorites/${songId}`)
}
