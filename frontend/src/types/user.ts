export type UserRole = 'ADMIN' | 'FINANCE' | 'COMPTABLE' | 'VIEWER'

export interface UserResponse {
  id: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface UserCreate {
  email: string
  full_name: string
  password: string
  role: UserRole
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface MessageResponse {
  message: string
}
