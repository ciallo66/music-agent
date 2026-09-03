// 播放行为上报接口。
import { http } from './http'

// 上报一次播放行为，供画像和推荐使用。
export function recordPlay(songId: number) {
  return http.post('/plays', { song_id: songId })
}
