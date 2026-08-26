import { http } from './http'

export interface ArtistBrief {
  id: number
  name: string
  avatar_url: string | null
}

export interface SongSummary {
  id: number
  title: string
  artist: ArtistBrief
  album: string | null
  genre: string | null
  language: string | null
  duration: number | null
  audio_url: string | null
  popularity: number
  bpm: number | null
  music_key: string | null
  energy: number | null
  valence: number | null
  danceability: number | null
}

export interface SongDetail extends SongSummary {
  lyrics: string | null
  loudness: number | null
  instruments: string | null
  song_structure: string | null
}

export interface SongPage {
  items: SongSummary[]
  total: number
  page: number
  page_size: number
}

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
