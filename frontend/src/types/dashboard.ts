export interface StatusBreakdown {
  UPLOADED: number
  PROCESSING: number
  PROCESSED: number
  REVIEW_REQUIRED: number
  ERROR: number
}

export interface FacturesTotales {
  total: number
  by_status: StatusBreakdown
}

export interface Alertes {
  pending_duplicates: number
  pending_anomalies: number
  total_pending: number
}

export interface Suspectes {
  count: number
}

export interface Evolution {
  labels: string[]
  uploaded: number[]
  processed: number[]
}

export interface TopFournisseurItem {
  supplier_name: string
  invoice_count: number
  total_amount_sum: number
}

export interface RisqueItem {
  supplier_name: string
  risk_score: number
}

export interface DashboardSummary {
  factures_totales: FacturesTotales
  alertes: Alertes
  suspectes: Suspectes
  evolution: Evolution
  top_fournisseurs: { items: TopFournisseurItem[] }
  risques: { items: RisqueItem[] }
}
