import { http } from './http'

export function recordPlay(songId: number) {
  return http.post('/plays', { song_id: songId })
}
