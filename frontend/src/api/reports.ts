import apiClient from './client'

function filenameFromHeader(headers: Headers, fallback: string): string {
  const cd = headers.get('content-disposition')
  if (cd) {
    const match = cd.match(/filename="?(.+?)"?\s*$/i)
    if (match) return match[1]
  }
  return fallback
}

export async function downloadDashboardReport(
  format: 'pdf' | 'excel',
  date_from?: string,
  date_to?: string,
): Promise<void> {
  const params: Record<string, string> = {}
  if (date_from) params.date_from = date_from
  if (date_to) params.date_to = date_to
  const response = await apiClient.get(`/api/v1/dashboard/export/${format}`, {
    params,
    responseType: 'blob',
  })
  const filename = filenameFromHeader(response.headers, `dashboard.${format}`)
  const blob = new Blob([response.data], { type: response.headers['content-type'] })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export async function downloadDuplicatesReport(
  format: 'pdf' | 'excel',
  date_from?: string,
  date_to?: string,
): Promise<void> {
  const params: Record<string, string> = {}
  if (date_from) params.date_from = date_from
  if (date_to) params.date_to = date_to
  const response = await apiClient.get(`/api/v1/duplicates/report/${format}`, {
    params,
    responseType: 'blob',
  })
  const filename = filenameFromHeader(response.headers, `doublons.${format}`)
  const blob = new Blob([response.data], { type: response.headers['content-type'] })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export interface DuplicateReportSummary {
  total_invoices_in_scope: number
  duplicate_count: number
  confirmed_count: number
  pending_count: number
  duplicate_rate: number
  montant_a_risque_total: number
  details: unknown[]
}

export async function getDuplicatesReportSummary(
  date_from?: string,
  date_to?: string,
): Promise<DuplicateReportSummary> {
  const params: Record<string, string> = {}
  if (date_from) params.date_from = date_from
  if (date_to) params.date_to = date_to
  const { data } = await apiClient.get<DuplicateReportSummary>(
    '/api/v1/duplicates/report/summary',
    { params },
  )
  return data
}

export interface SupplierDetail {
  supplier_name: string
  risk_score: number
  risk_level: string
  total_invoices: number
  total_sum: number
  avg_amount: number
  min_amount: number
  max_amount: number
  std_amount: number
  frequence: {
    invoices_per_month: number
    avg_days_between_invoices: number | null
  }
  historique: Array<{
    invoice_id: string
    invoice_number: string
    invoice_date: string
    total_amount: number
    tax_amount: number
    status: string
    has_anomaly: boolean
    has_duplicate: boolean
  }>
  anomalies: Array<{
    id: string
    invoice_id: string
    alert_type: string
    severity: string
    description: string
    metric_value: number
    threshold_value: number
    status: string
    created_at: string
    invoice_number: string
    invoice_date: string
  }>
}

export async function getSupplierDetail(
  supplierName: string,
  date_from?: string,
  date_to?: string,
): Promise<SupplierDetail> {
  const params: Record<string, string> = {}
  if (date_from) params.date_from = date_from
  if (date_to) params.date_to = date_to
  const { data } = await apiClient.get<SupplierDetail>(
    `/api/v1/analysis/suppliers/${encodeURIComponent(supplierName)}/detail`,
    { params },
  )
  return data
}

export async function downloadSupplierReport(
  supplierName: string,
  format: 'pdf' | 'excel',
  date_from?: string,
  date_to?: string,
): Promise<void> {
  const params: Record<string, string> = {}
  if (date_from) params.date_from = date_from
  if (date_to) params.date_to = date_to
  const response = await apiClient.get(
    `/api/v1/analysis/suppliers/${encodeURIComponent(supplierName)}/report/${format}`,
    { params, responseType: 'blob' },
  )
  const filename = filenameFromHeader(response.headers, `fournisseur_${supplierName}.${format}`)
  const blob = new Blob([response.data], { type: response.headers['content-type'] })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export interface ExpenseEvolutionResponse {
  period_n: {
    label: string
    total: number
    buckets: Array<{ period_label: string; amount: number }>
  }
  period_n_minus_1: {
    label: string
    total: number
    buckets: Array<{ period_label: string; amount: number }>
  }
  variation_pct: number
  variation_direction: string
}

export async function getExpenseEvolution(
  date_from: string,
  date_to: string,
  granularity: string,
): Promise<ExpenseEvolutionResponse> {
  const { data } = await apiClient.get<ExpenseEvolutionResponse>(
    '/api/v1/analysis/expense-evolution',
    { params: { date_from, date_to, granularity } },
  )
  return data
}
