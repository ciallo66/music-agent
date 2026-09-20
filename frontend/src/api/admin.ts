// 管理后台接口：概览统计、账号管理，以及曲目/歌手的增删改。
import { http } from './http'
import type { SongDetail, SongSummary } from '../types/music'

// --- 类型 ---

export interface AdminCountItem {
  label: string
  count: number
}

export interface AdminOverview {
  songs: number
  artists: number
  users: number
  admins: number
  playlists: number
  feedback: number
  favorites: number
  plays: number
  knowledge: number
  import_jobs: number
  songs_with_embedding: number
  songs_with_audio_features: number
  genre_distribution: AdminCountItem[]
}

export interface AdminUserItem {
  id: number
  username: string
  role: string
  status: string
  created_at: string
  favorites: number
  playlists: number
  feedback: number
}

export interface AdminUserPage {
  items: AdminUserItem[]
  total: number
  page: number
  page_size: number
}

export interface AdminArtistItem {
  id: number
  name: string
  avatar_url: string | null
}

export interface AdminSongListItem extends SongSummary {
  created_at?: string
}

// --- 概览与账号 ---

export function getAdminOverview() {
  return http.get<AdminOverview>('/admin/overview')
}

export function listAdminUsers(
  params: { keyword?: string; page?: number; page_size?: number } = {},
) {
  return http.get<AdminUserPage>('/admin/users', { params })
}

export function updateAdminUser(
  userId: number,
  payload: { role?: string; status?: string },
  params: { keyword?: string; page?: number; page_size?: number } = {},
) {
  return http.patch<AdminUserPage>(`/admin/users/${userId}`, payload, { params })
}

// --- 曲目与歌手 ---

export function listAdminSongs(
  params: { q?: string; genre?: string; page?: number; page_size?: number } = {},
) {
  // 空关键词不要发出去：后端对 q 有长度约束，发 q= 会 422，
  // 后台「曲目管理」页就会一直是空表（这就是线上看不到 931 首歌的原因）。
  const { q, genre, ...rest } = params
  return http.get<{ items: SongSummary[]; total: number; page: number; page_size: number }>(
    '/songs',
    { params: { ...rest, ...(q ? { q } : {}), ...(genre ? { genre } : {}) } },
  )
}

export function createAdminSong(payload: Record<string, unknown>) {
  return http.post<SongDetail>('/admin/songs', payload)
}

export function updateAdminSong(songId: number, payload: Record<string, unknown>) {
  return http.patch<SongDetail>(`/admin/songs/${songId}`, payload)
}

export function deleteAdminSong(songId: number) {
  return http.delete(`/admin/songs/${songId}`)
}

export function listAdminArtists(params: { q?: string; page?: number; page_size?: number } = {}) {
  // 同上：空 q 不发，避免后端 422 导致歌手列表空白
  const { q, ...rest } = params
  return http.get<{ items: AdminArtistItem[]; total: number; page: number; page_size: number }>(
    '/artists',
    { params: { ...rest, ...(q ? { q } : {}) } },
  )
}

export function createAdminArtist(payload: { name: string; avatar_url?: string | null }) {
  return http.post<AdminArtistItem>('/admin/artists', payload)
}

export function updateAdminArtist(
  artistId: number,
  payload: { name?: string; avatar_url?: string | null },
) {
  return http.patch<AdminArtistItem>(`/admin/artists/${artistId}`, payload)
}

export function deleteAdminArtist(artistId: number) {
  return http.delete(`/admin/artists/${artistId}`)
}
