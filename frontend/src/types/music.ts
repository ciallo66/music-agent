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
  audio_url: string | null
  popularity: number
  bpm: number | null
  music_key: string | null
  energy: number | null
  valence: number | null
  danceability: number | null
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

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}

export interface RecommendationItem extends SongSummary {
  reason: string
}

export interface RecommendationPage {
  items: RecommendationItem[]
  strategy: 'content' | 'popular_fallback'
}
