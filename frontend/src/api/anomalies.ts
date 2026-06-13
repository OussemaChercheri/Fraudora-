import type {
  AnomalyAlertResponse,
  PendingAnomaliesResponse,
  SupplierRiskScoreResponse,
} from '../types/anomaly'
import type { AlertType, Severity } from '../types/anomaly'
import apiClient from './client'

export async function getAnomalyAlerts(
  invoiceId: string,
): Promise<AnomalyAlertResponse[]> {
  const { data } = await apiClient.get<AnomalyAlertResponse[]>(
    `/api/v1/anomalies/invoice/${invoiceId}`,
  )
  return data
}

export async function reviewAnomalyAlert(
  alertId: string,
  status: 'ACKNOWLEDGED' | 'DISMISSED',
): Promise<AnomalyAlertResponse> {
  const { data } = await apiClient.put<AnomalyAlertResponse>(
    `/api/v1/anomalies/${alertId}/review`,
    { status },
  )
  return data
}

export async function getPendingAnomalies(params: {
  page?: number
  page_size?: number
  alert_type?: AlertType
  severity?: Severity
} = {}): Promise<PendingAnomaliesResponse> {
  const { data } = await apiClient.get<PendingAnomaliesResponse>(
    '/api/v1/anomalies/pending',
    { params },
  )
  return data
}

export async function getSupplierRiskScores(
  min_risk_score?: number,
): Promise<SupplierRiskScoreResponse[]> {
  const { data } = await apiClient.get<SupplierRiskScoreResponse[]>(
    '/api/v1/anomalies/suppliers/risk-scores',
    { params: { min_risk_score } },
  )
  return data
}

export async function recomputeRiskScores(): Promise<{
  recomputed: number
  message: string
}> {
  const { data } = await apiClient.post<{
    recomputed: number
    message: string
  }>('/api/v1/anomalies/suppliers/recompute')
  return data
}
