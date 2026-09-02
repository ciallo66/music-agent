import { http } from './http'
import type { MusicProfileResponse } from '../types/profile'

export function getMusicProfile() {
  return http.get<MusicProfileResponse>('/me/music-profile')
}
