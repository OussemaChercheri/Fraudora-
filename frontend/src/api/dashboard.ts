import type { DashboardSummary } from '../types/dashboard'
import apiClient from './client'

export async function getDashboardSummary(
  date_from?: string,
  date_to?: string,
): Promise<DashboardSummary> {
  const params: Record<string, string> = {}
  if (date_from) params.date_from = date_from
  if (date_to) params.date_to = date_to
  const { data } = await apiClient.get<DashboardSummary>('/api/v1/dashboard/summary', { params })
  return data
}
