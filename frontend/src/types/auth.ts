// 认证响应和用户资料的共享类型。
export interface UserProfile {
  id: number
  username: string
  role: 'user' | 'admin'
  status: 'active' | 'disabled'
  created_at: string
  /** 能否改动后台数据（服务端判定：管理员角色且不是演示账号）。 */
  can_manage_data: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}
