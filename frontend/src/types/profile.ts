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
}
