import type { UserCreate, UserResponse } from '../types/user'
import apiClient from './client'

export async function fetchUsers(): Promise<UserResponse[]> {
  const { data } = await apiClient.get<UserResponse[]>('/api/v1/admin/users/')
  return data
}

export async function createUser(user: UserCreate): Promise<UserResponse> {
  const { data } = await apiClient.post<UserResponse>(
    '/api/v1/admin/users/',
    user,
  )
  return data
}

export async function deactivateUser(userId: string): Promise<UserResponse> {
  const { data } = await apiClient.delete<UserResponse>(
    `/api/v1/admin/users/${userId}/deactivate`,
  )
  return data
}
