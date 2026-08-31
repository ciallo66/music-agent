export interface UserProfile {
  id: number
  username: string
  role: 'user' | 'admin'
  status: 'active' | 'disabled'
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}
