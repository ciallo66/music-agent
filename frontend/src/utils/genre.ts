// 流派判定：把 AcousticBrainz 多个分类体系的结果做投票融合，得出页面展示用的流派。
// 库里 genre 字段是单一体系（rosamerica）的结果，这里改为多体系投票，并保留可解释的置信度。
// 注意：这是模型判定，不是官方流派标签，界面需按「模型判定」表述。

/** 多体系分类码到统一中文类的映射；未列出的码不参与投票。 */
const TAXONOMY_MAP: Record<string, Record<string, string>> = {
  rosamerica: {
    cla: '古典',
    roc: '摇滚',
    rhy: '节奏布鲁斯',
    pop: '流行',
    dan: '舞曲',
    jaz: '爵士',
    hip: '嘻哈',
    spe: '语音',
  },
  tzanetakis: {
    cla: '古典',
    roc: '摇滚',
    pop: '流行',
    hip: '嘻哈',
    blu: '节奏布鲁斯',
    jaz: '爵士',
    met: '摇滚',
    dis: '舞曲',
    cou: '乡村',
  },
  electronic: {
    house: '舞曲',
    techno: '舞曲',
    trance: '舞曲',
    dubstep: '舞曲',
    drumandbass: '舞曲',
    ambient: '氛围',
    downtempo: '氛围',
    breakbeat: '舞曲',
  },
  dortmund: {
    rock: '摇滚',
    pop: '流行',
    jazz: '爵士',
    blues: '节奏布鲁斯',
    rap: '嘻哈',
    electronic: '舞曲',
    folkcountry: '乡村',
    classical: '古典',
  },
}

/** 投票结果：类名 + 得票数 + 参与投票的体系数。 */
export interface GenreVote {
  name: string
  votes: number
  total: number
}

/**
 * 对多体系标签投票，返回得票最高的流派。
 * @param labels - 形如 `{ rosamerica: 'roc', tzanetakis: 'jaz', ... }`，值可能为 null。
 * @returns 得票最高项；无法投票时返回 null。
 */
export function fusedGenre(labels: Record<string, string> | null): GenreVote | null {
  if (!labels) return null
  const tally = new Map<string, number>()
  let total = 0
  for (const [taxonomy, code] of Object.entries(labels)) {
    const mapped = TAXONOMY_MAP[taxonomy]?.[code]
    if (!mapped) continue
    tally.set(mapped, (tally.get(mapped) ?? 0) + 1)
    total += 1
  }
  if (total === 0) return null
  let best: GenreVote | null = null
  for (const [name, votes] of tally) {
    if (best === null || votes > best.votes) best = { name, votes, total }
  }
  return best
}

/** 把投票结果渲染成一句可读说明，例如「舞曲（3/4 个体系一致）」。 */
export function fusedGenreLabel(labels: Record<string, string> | null): string {
  const vote = fusedGenre(labels)
  if (vote === null) return ''
  if (vote.total === 1) return vote.name
  return `${vote.name}（${vote.votes}/${vote.total} 个分类体系一致）`
}
