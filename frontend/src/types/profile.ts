// 音乐画像接口返回的统计、趋势和偏好类型。
import type { SongSummary } from './music'

export interface MusicFeatureProfile {
  average_bpm: number | null
  average_energy: number | null
  average_valence: number | null
  average_danceability: number | null
}

export interface MusicDistributionItem {
  name: string
  count: number
}

export interface PlayTrendItem {
  date: string
  count: number
}

export interface RecentPlayItem {
  played_at: string
  song: SongSummary
}

export interface PreferenceChangeItem {
  direction: string
  detail: string
}

export interface ActiveHourItem {
  hour: number
  label: string
  weight: number
}

export interface InterestDistributionItem {
  label: string
  weight: number
}

export interface MusicProfileResponse {
  total_plays: number
  unique_songs: number
  favorite_count: number
  preferred_genres: string[]
  feature_profile: MusicFeatureProfile
  genre_distribution: MusicDistributionItem[]
  top_artists: MusicDistributionItem[]
  play_trend: PlayTrendItem[]
  recent_plays: RecentPlayItem[]
  preference_change?: PreferenceChangeItem[]
  active_hours?: ActiveHourItem[]
  favorite_trend?: PlayTrendItem[]
  agent_interpretation?: string
  interest_distribution?: InterestDistributionItem[]
}
