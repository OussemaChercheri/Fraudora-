import type { MessageResponse, TokenResponse } from '../types/user'
import apiClient from './client'

export async function loginUser(
  email: string,
  password: string,
): Promise<TokenResponse> {
  const params = new URLSearchParams()
  params.append('username', email)
  params.append('password', password)

  const { data } = await apiClient.post<TokenResponse>(
    '/api/v1/auth/login',
    params,
    {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    },
  )
  return data
}

export async function forgotPassword(email: string): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>(
    '/api/v1/auth/forgot-password',
    { email },
  )
  return data
}

export async function resetPassword(
  token: string,
  newPassword: string,
): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>(
    '/api/v1/auth/reset-password',
    { token, new_password: newPassword },
  )
  return data
}

export async function logoutUser(): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>('/api/v1/auth/logout')
  return data
}
