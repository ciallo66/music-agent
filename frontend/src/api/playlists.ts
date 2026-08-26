import { http } from './http'

export interface ArtistBrief {
  id: number
  name: string
  avatar_url: string | null
}

export interface SongBrief {
  id: number
  title: string
  artist: ArtistBrief
  album: string | null
  genre: string | null
  duration: number | null
  audio_url: string | null
  popularity: number
}

export interface PlaylistItem {
  id: number
  name: string
  description: string | null
  song_count: number
  created_at: string
}

export interface PlaylistDetail extends PlaylistItem {
  songs: SongBrief[]
}

export function listPlaylists() {
  return http.get<{ items: PlaylistItem[] }>('/playlists')
}

export function getPlaylist(id: number) {
  return http.get<PlaylistDetail>(`/playlists/${id}`)
}

export function createPlaylist(payload: { name: string; description?: string }) {
  return http.post<PlaylistItem>('/playlists', payload)
}

export function updatePlaylist(id: number, payload: { name?: string; description?: string }) {
  return http.patch<PlaylistItem>(`/playlists/${id}`, payload)
}

export function deletePlaylist(id: number) {
  return http.delete(`/playlists/${id}`)
}

export function addSongToPlaylist(playlistId: number, songId: number) {
  return http.post(`/playlists/${playlistId}/songs`, { song_id: songId })
}

export function removeSongFromPlaylist(playlistId: number, songId: number) {
  return http.delete(`/playlists/${playlistId}/songs/${songId}`)
}
