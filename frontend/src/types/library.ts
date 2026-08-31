import type { PlaylistDetail, PlaylistItem } from './music'

export interface FavoriteItem {
  id: number
  song_id: number
  created_at: string
}

export interface FavoritePage {
  items: FavoriteItem[]
}

export interface PlaylistPage {
  items: PlaylistItem[]
}

export interface PlaylistCreatePayload {
  name: string
  description?: string
}

export interface PlaylistUpdatePayload {
  name?: string
  description?: string
}

export type { PlaylistDetail, PlaylistItem }
