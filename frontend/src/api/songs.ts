// 歌曲目录查询与详情接口。
import { http } from './http'
import type { SongDetail, SongPage } from '../types/music'
export type { SongDetail, SongPage, SongSummary } from '../types/music'

// 分页查询歌曲目录，参数保持与后端筛选协议一致。
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

// 获取单首歌曲详情及音频特征。
export function getSong(id: number) {
  return http.get<SongDetail>(`/songs/${id}`)
}

// 获取目录中实际存在的风格列表，供筛选下拉使用（避免前后端硬编码不一致）。
export function listSongGenres() {
  return http.get<string[]>('/songs/genres')
}
