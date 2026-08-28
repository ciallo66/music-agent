import { http } from './http'
import type { PlaylistDetail, PlaylistItem, SongSummary } from '../types/music'
export type { PlaylistDetail, PlaylistItem } from '../types/music'
export type SongBrief = SongSummary

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
