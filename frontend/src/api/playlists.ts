// 歌单及歌曲关联接口。
import { http } from './http'
import type {
  PlaylistCreatePayload,
  PlaylistDetail,
  PlaylistItem,
  PlaylistPage,
  PlaylistUpdatePayload,
} from '../types/library'
export type { PlaylistDetail, PlaylistItem } from '../types/library'

// 查询当前用户歌单。
export function listPlaylists() {
  return http.get<PlaylistPage>('/playlists')
}

// 查询歌单详情及歌曲。
export function getPlaylist(id: number) {
  return http.get<PlaylistDetail>(`/playlists/${id}`)
}

// 创建歌单。
export function createPlaylist(payload: PlaylistCreatePayload) {
  return http.post<PlaylistItem>('/playlists', payload)
}

// 更新歌单基础信息。
export function updatePlaylist(id: number, payload: PlaylistUpdatePayload) {
  return http.patch<PlaylistItem>(`/playlists/${id}`, payload)
}

// 删除歌单。
export function deletePlaylist(id: number) {
  return http.delete(`/playlists/${id}`)
}

// 向歌单追加歌曲。
export function addSongToPlaylist(playlistId: number, songId: number) {
  return http.post(`/playlists/${playlistId}/songs`, { song_id: songId })
}

// 从歌单移除歌曲。
export function removeSongFromPlaylist(playlistId: number, songId: number) {
  return http.delete(`/playlists/${playlistId}/songs/${songId}`)
}
