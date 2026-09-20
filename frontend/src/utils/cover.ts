// 排版封面的配色：由**歌曲自带字段**派生，任何页面算出来都一样。
//
// 为什么是「流派定色相 + 节拍定明暗」：
// 配色必须只依赖列表接口与详情接口**都返回**的字段，否则同一首歌在
// 曲库列表和详情页会显示成两种颜色。列表接口只给 genre（中文单值）、
// bpm、danceability 这些，genre_labels / mood_labels 只有详情页才有。

/** 一套设计过的色相，按流派分配；不在表里的风格走默认值。 */
const GENRE_HUES: Record<string, number> = {
  古典: 38, // 琥珀
  爵士: 268, // 靛紫
  摇滚: 352, // 朱红
  流行: 172, // 青绿
  舞曲: 304, // 品红
  节奏布鲁斯: 318, // 梅红
  嘻哈: 22, // 赭橙
  语音: 208, // 灰蓝
  电子: 190, // 电青
}

/** 未知流派的兜底色相：偏中性的蓝，不与任何一种已知风格撞色。 */
const FALLBACK_HUE = 222

/** 稳定哈希：同样的输入永远得到同样的数值，用于微扰。 */
function hash(input: string): number {
  let value = 2166136261
  for (let index = 0; index < input.length; index += 1) {
    value ^= input.charCodeAt(index)
    value = Math.imul(value, 16777619)
  }
  return Math.abs(value)
}

export interface CoverPalette {
  /** 色相（0-360），由流派决定 */
  hue: number
  /** 渐变两端与字色，直接可用的 CSS 颜色 */
  from: string
  to: string
  text: string
  /** 角标用的浅色描边色 */
  accent: string
}

export interface CoverSource {
  /** 歌曲主键：只用于微扰，保证同一首歌稳定 */
  id: number
  title: string
  genre?: string | null
  bpm?: number | null
  danceability?: number | null
}

/**
 * 由歌曲字段算出一套封面配色。
 *
 * - 色相：流派决定，所以「摇滚都是暖红、古典都是琥珀」，扫一眼能分出来
 * - 明度/饱和度：节拍决定，快歌更亮更饱和、慢歌更沉
 * - 微扰：用 id 与标题做一点偏移，避免同流派同一色
 */
export function coverPalette(song: CoverSource): CoverPalette {
  const genre = (song.genre ?? '').trim()
  const baseHue = GENRE_HUES[genre] ?? FALLBACK_HUE
  const jitter = (hash(`${song.id}:${song.title}`) % 17) - 8
  const hue = (baseHue + jitter + 360) % 360

  // 节拍：0 → 沉稳，180+ → 明快；缺省按中速处理
  const bpm = typeof song.bpm === 'number' && Number.isFinite(song.bpm) ? song.bpm : 110
  const tempo = Math.min(1, Math.max(0, (bpm - 60) / 120))
  // 律动给一点额外亮度，但权重低，避免盖过流派的主导作用
  const groove =
    typeof song.danceability === 'number' && Number.isFinite(song.danceability)
      ? Math.min(1, Math.max(0, song.danceability))
      : 0.5

  const fromLight = 30 + tempo * 14
  const toLight = 16 + tempo * 10
  const saturation = 34 + tempo * 16 + groove * 6

  return {
    hue,
    from: `hsl(${hue.toFixed(0)} ${saturation.toFixed(0)}% ${fromLight.toFixed(0)}%)`,
    to: `hsl(${((hue + 26) % 360).toFixed(0)} ${(saturation - 10).toFixed(0)}% ${toLight.toFixed(0)}%)`,
    text: `hsl(${hue.toFixed(0)} 82% 86%)`,
    accent: `hsl(${hue.toFixed(0)} 70% 68%)`,
  }
}

/** 取封面上那个大字：中文取首字，英文取首字母，忽略引号与括号。 */
export function coverGlyph(title: string): string {
  const cleaned = title.replace(/^[\s"'“”‘’(\[（【]+/, '').trim()
  if (!cleaned) return '♪'
  return cleaned.slice(0, 1).toUpperCase()
}

/**
 * 数据来源的短标记。
 *
 * 把「数据来自哪」变成封面的一部分：AcousticBrainz 提供音频分析，
 * Jamendo 提供元数据。没有来源字段时不显示，不编造。
 */
export function sourceBadge(source?: string | null): string {
  if (!source) return ''
  const key = source.trim().toLowerCase()
  if (key === 'acousticbrainz') return 'AB'
  if (key === 'jamendo') return 'Jam'
  return source.trim().slice(0, 3)
}
