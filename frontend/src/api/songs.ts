import { http } from './http'
import type { SongDetail, SongPage } from '../types/music'
export type { SongDetail, SongPage, SongSummary } from '../types/music'

export function listSongs(params: {
  page?: number
  page_size?: number
  q?: string
  genre?: string
  language?: string
  artist_id?: number
  bpm_min?: number
  bpm_max?: number
}) {
  return http.get<SongPage>('/songs', { params })
}

export function getSong(id: number) {
  return http.get<SongDetail>(`/songs/${id}`)
}
