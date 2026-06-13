export type AlertType = 'ABNORMAL_AMOUNT' | 'NEW_HIGH_RISK_SUPPLIER' | 'PRICE_SPIKE'

export type Severity = 'LOW' | 'MEDIUM' | 'HIGH'

export type AlertStatus = 'PENDING' | 'ACKNOWLEDGED' | 'DISMISSED' | 'PROCESSED'

export interface InvoiceSummary {
  id: string
  original_filename: string
  invoice_number: string | null
  supplier_name: string | null
  total_amount: number | null
  invoice_date: string | null
}

export interface AnomalyAlertResponse {
  id: string
  invoice_id: string
  alert_type: AlertType
  severity: Severity
  description: string
  metric_value: number
  threshold_value: number
  status: AlertStatus
  acknowledged_by_user_id: string | null
  acknowledged_at: string | null
  created_at: string
  invoice: InvoiceSummary
}

export interface PendingAnomaliesResponse {
  items: AnomalyAlertResponse[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface SupplierRiskScoreResponse {
  id: string
  supplier_name: string
  risk_score: number
  total_invoices: number
  total_amount_sum: number
  avg_amount: number
  std_amount: number
  anomaly_count: number
  last_invoice_date: string | null
  first_seen_date: string | null
  updated_at: string
}
