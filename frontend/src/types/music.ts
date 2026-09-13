// 音乐领域对象：歌手、歌曲、歌单和推荐结果。
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
  /** 后端兼容字段；前端不展示、不调用音频资源。 */
  audio_url: string | null
  popularity: number
  bpm: number | null
  music_key: string | null
  energy: number | null
  valence: number | null
  danceability: number | null
}

export interface SongPage {
  items: SongSummary[]
  total: number
  page: number
  page_size: number
}

export interface SongDetail extends SongSummary {
  lyrics: string | null
  loudness: number | null
  instruments: string | null
  song_structure: string | null
}

export interface PlaylistItem {
  id: number
  name: string
  description: string | null
  song_count: number
  created_at: string
}

export interface PlaylistDetail extends PlaylistItem {
  songs: SongSummary[]
}

export interface RecommendationItem extends SongSummary {
  reason: string
}

export interface RecommendationPage {
  items: RecommendationItem[]
  strategy: 'content' | 'popular_fallback'
}
