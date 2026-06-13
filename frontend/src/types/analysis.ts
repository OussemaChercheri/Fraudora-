export interface StatusBreakdown {
  UPLOADED: number
  PROCESSING: number
  PROCESSED: number
  REVIEW_REQUIRED: number
  ERROR: number
}

export interface ProcessingSummary {
  total_invoices: number
  by_status: StatusBreakdown
  processed_rate: number
  review_required_rate: number
  error_rate: number
  avg_processing_time_ms: number
  total_pages_processed: number
}

export interface OcrQualityStats {
  avg_confidence: Record<string, number>
  field_extraction_rate: Record<string, number>
  manually_corrected_count: number
  manually_corrected_rate: number
}

export interface SupplierSummaryItem {
  supplier_name: string
  invoice_count: number
  total_amount_sum: number
  avg_amount: number
  min_amount: number
  max_amount: number
  first_seen: string | null
  last_seen: string | null
}

export interface MonthlyVolumeItem {
  month: string
  count: number
  processed_count: number
}

export const OCR_FIELD_LABELS: Record<string, string> = {
  invoice_number: 'N° facture',
  invoice_date: 'Date facture',
  supplier_name: 'Fournisseur',
  total_amount: 'Montant TTC',
  tax_amount: 'TVA',
}

export const OCR_FIELD_KEYS = [
  'invoice_number',
  'invoice_date',
  'supplier_name',
  'total_amount',
  'tax_amount',
] as const
