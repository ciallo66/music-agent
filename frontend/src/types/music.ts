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
  /** 多体系流派标签（AcousticBrainz），用于投票判定展示流派；列表接口可能不返回。 */
  genre_labels?: Record<string, string> | null
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
  /** 音频分析派生特征（AcousticBrainz）。字段都可能为空，展示时按缺失处理。 */
  voice_instrumental: string | null
  voice_probability: number | null
  /** 节奏特征：bpm / onset_rate / beats_count。 */
  rhythm_features: Record<string, number> | null
  /** 调性特征：key_key / key_scale / chords_key / chords_scale / key_strength。 */
  tonal_features: Record<string, string | number> | null
  /** 频谱特征：每个键是 {mean,max,min,var,...} 结构。 */
  spectral_features: Record<string, unknown> | null
  mood_labels: Record<string, string> | null
  genre_labels: Record<string, string> | null
  feature_completeness: number | null
}

// --- 音频分析标签的中文映射（键来自 AcousticBrainz，值为 not_xxx 表示未命中） ---

/** 情绪标签：中文名与取值键。 */
const MOOD_KEYS: { key: string; label: string }[] = [
  { key: 'happy', label: '明亮' },
  { key: 'sad', label: '忧伤' },
  { key: 'relaxed', label: '放松' },
  { key: 'party', label: '派对' },
  { key: 'aggressive', label: '激烈' },
  { key: 'acoustic', label: '原声' },
  { key: 'electronic', label: '电子' },
]

/** 取歌曲命中的情绪标签；值为 not_xxx 视为未命中，空数据返回空数组。 */
export function moodTags(labels: Record<string, string> | null): string[] {
  if (!labels) return []
  return MOOD_KEYS.filter(({ key }) => {
    const value = labels[key]
    return typeof value === 'string' && value !== '' && !value.startsWith('not_')
  }).map(({ label }) => label)
}

/** 人声 / 器乐的中文说法；未知值原样返回。 */
export function voiceLabel(voiceInstrumental: string | null): string {
  if (!voiceInstrumental) return ''
  const labels: Record<string, string> = { instrumental: '器乐', voice: '人声', vocal: '人声' }
  return labels[voiceInstrumental] ?? voiceInstrumental
}

/**
 * 律动的三档中文说法。
 *
 * `danceability` 取自 AcousticBrainz 的 danceability 分类器，是「判定为可舞动」的
 * 概率，而不是连续刻度：库里 931 首有 364 首落在 0 附近、244 首落在 1 附近。
 * 直接按百分比展示会出现大批「0% 律动」，含义也被误读成「没有律动」，
 * 因此按档位展示，精确分值放进 title 提示里备查。
 */
export function danceabilityLabel(value: number | null | undefined): string {
  if (value === null || value === undefined) return ''
  if (value < 0.05) return '低'
  if (value > 0.95) return '高'
  return '中'
}

/** 律动的百分比文本，保留给提示与详情页使用。 */
export function danceabilityPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-'
  return `${Math.round(value * 100)}%`
}

/** 律动单元格的悬浮说明：说明档位含义，并给出模型的精确分值。 */
export function danceabilityHint(value: number | null | undefined): string {
  if (value === null || value === undefined) return '这首没有可用的律动分析结果'
  const percent = Math.round(value * 100)
  if (percent === 0) return '律动：模型判断为可舞动的概率约 0%'
  if (percent === 100) return '律动：模型判断为可舞动的概率接近 100%'
  return `律动：模型判断为可舞动的概率约 ${percent}%`
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
  match_score: number | null
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
