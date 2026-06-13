import type { NotificationListResponse, NotificationResponse } from '../types/notification'
import apiClient from './client'

export async function getNotifications(params: {
  page?: number
  page_size?: number
  unread_only?: boolean
}): Promise<NotificationListResponse> {
  const { data } = await apiClient.get<NotificationListResponse>('/api/v1/notifications/', { params })
  return data
}

export async function markAsRead(id: string): Promise<NotificationResponse> {
  const { data } = await apiClient.put<NotificationResponse>(`/api/v1/notifications/${id}/read`)
  return data
}

export async function markAllRead(): Promise<{ updated: number; message: string }> {
  const { data } = await apiClient.put<{ updated: number; message: string }>('/api/v1/notifications/read-all')
  return data
}
