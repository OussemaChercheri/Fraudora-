import type { UserResponse } from '../types/user'

export function parseUserFromToken(token: string): UserResponse {
  const payload = JSON.parse(
    atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')),
  ) as { sub: string; email: string; role: UserResponse['role'] }

  return {
    id: payload.sub,
    email: payload.email,
    full_name: payload.email.split('@')[0],
    role: payload.role,
    is_active: true,
    created_at: new Date().toISOString(),
  }
}

export const ACCESS_TOKEN_KEY = 'access_token'

export function getStoredToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}
