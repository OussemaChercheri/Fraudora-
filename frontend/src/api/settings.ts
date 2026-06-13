import type { AlertThresholdResponse } from '../types/settings'
import apiClient from './client'

export async function getThresholds(): Promise<AlertThresholdResponse[]> {
  const { data } = await apiClient.get<AlertThresholdResponse[]>('/api/v1/settings/thresholds')
  return data
}

export async function updateThreshold(
  key: string,
  threshold_value: number,
): Promise<AlertThresholdResponse> {
  const { data } = await apiClient.put<AlertThresholdResponse>(
    `/api/v1/settings/thresholds/${key}`,
    { threshold_value },
  )
  return data
}
