export type NotificationType = 'DUPLICATE_ALERT' | 'ANOMALY_ALERT' | 'INVOICE_PROCESSED' | 'INVOICE_ERROR' | 'SYSTEM'

export interface NotificationResponse {
  id: string
  user_id: string
  title: string
  message: string
  notification_type: NotificationType
  related_invoice_id: string | null
  is_read: boolean
  created_at: string
}

export interface NotificationListResponse {
  items: NotificationResponse[]
  total: number
  unread_count: number
}
