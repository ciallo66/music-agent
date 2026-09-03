// 个人音乐画像接口。
import { http } from './http'
import type { MusicProfileResponse } from '../types/profile'

// 获取当前用户的音乐画像统计。
export function getMusicProfile() {
  return http.get<MusicProfileResponse>('/me/music-profile')
}
