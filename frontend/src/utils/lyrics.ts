export interface LyricLine {
  time: number
  text: string
}

/** 将 LRC 文本解析为按时间升序排列的歌词行。 */
export function parseLrc(input: string): LyricLine[] {
  const lines: LyricLine[] = []
  const pattern = /\[(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?\](.*)/g

  for (const rawLine of input.split(/\r?\n/)) {
    for (const match of rawLine.matchAll(pattern)) {
      const minutes = Number(match[1])
      const seconds = Number(match[2])
      const fraction = match[3] ? Number(`0.${match[3]}`) : 0
      const text = match[4].trim()
      if (Number.isFinite(minutes) && seconds < 60 && text) {
        lines.push({ time: minutes * 60 + seconds + fraction, text })
      }
    }
  }

  return lines.sort((left, right) => left.time - right.time)
}
