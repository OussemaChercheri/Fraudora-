export interface AlertThresholdResponse {
  id: string
  threshold_key: string
  threshold_value: number
  description: string
  updated_by_user_id: string | null
  updated_at: string
}
