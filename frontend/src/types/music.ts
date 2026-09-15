// 音乐领域对象：歌手、歌曲、歌单、推荐结果和反馈。
// 音乐领域对象：歌手、歌曲、歌单、推荐结果和反馈。
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

// --- 推荐相关 ---

export type FeedbackAction = 'like' | 'dislike' | 'seen' | 'similar' | 'less'

export interface FeedbackActionItem {
  action: FeedbackAction
  label: string
  description: string
}

export interface RecommendationItem extends SongSummary {
  reason: string
}

export interface RecommendationPage {
  items: RecommendationItem[]
  strategy: 'content' | 'popular_fallback'
}

export interface StructuredRecommendationCard {
  title: string
  items: StructuredRecommendationItem[]
  reason: string
  tags: string[]
  scenario: string
  feedback_actions: FeedbackAction[]
}

export interface StructuredRecommendationItem extends SongSummary {
  reason: string
  match_score: number
}

export interface FeedbackStats {
  total: number
  liked_count: number
  disliked_count: number
  seen_count: number
}

export interface RecommendationFeedbackResponse {
  song_id: number
  action: string
  created_at: string
}
