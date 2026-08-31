import { http } from './http'
import type {
  PlaylistCreatePayload,
  PlaylistDetail,
  PlaylistItem,
  PlaylistPage,
  PlaylistUpdatePayload,
} from '../types/library'
export type { PlaylistDetail, PlaylistItem } from '../types/library'

export function listPlaylists() {
  return http.get<PlaylistPage>('/playlists')
}

export function getPlaylist(id: number) {
  return http.get<PlaylistDetail>(`/playlists/${id}`)
}

export function createPlaylist(payload: PlaylistCreatePayload) {
  return http.post<PlaylistItem>('/playlists', payload)
}

export function updatePlaylist(id: number, payload: PlaylistUpdatePayload) {
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
