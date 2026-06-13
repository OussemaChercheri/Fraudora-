export type InvoiceStatus =
  | 'UPLOADED'
  | 'PROCESSING'
  | 'PROCESSED'
  | 'REVIEW_REQUIRED'
  | 'ERROR'

export type FileType = 'PDF' | 'JPG' | 'PNG'

export interface InvoiceResponse {
  id: string
  user_id: string
  original_filename: string
  file_type: FileType
  file_size_kb: number
  status: InvoiceStatus
  has_anomaly_alert: boolean
  created_at: string
}

export interface InvoiceDetailResponse extends InvoiceResponse {
  ocr_raw_text: string | null
}

export interface InvoiceListResponse {
  items: InvoiceResponse[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface BulkUploadItemResult {
  filename: string
  status: string
  invoice_id?: string
  error_message?: string
}

export interface BulkUploadResponse {
  results: BulkUploadItemResult[]
}

export interface InvoiceDataField<T = string | number | null> {
  value: T
  confidence: number
  needs_review: boolean
}

export interface InvoiceDataResponse {
  id: string
  invoice_id: string
  invoice_number: InvoiceDataField<string | null>
  invoice_date: InvoiceDataField<string | null>
  supplier_name: InvoiceDataField<string | null>
  total_amount: InvoiceDataField<number | null>
  tax_amount: InvoiceDataField<number | null>
  is_manually_corrected: boolean
  correction_history: Array<{
    field: string
    old_value: string | number | null
    new_value: string | number | null
    corrected_by: string
    corrected_at: string
  }>
  created_at: string
  updated_at: string
}

export interface InvoiceDataUpdate {
  invoice_number?: string
  invoice_date?: string
  supplier_name?: string
  total_amount?: number
  tax_amount?: number
}

export interface GetInvoicesParams {
  page?: number
  page_size?: number
  status?: InvoiceStatus
  date_from?: string
  date_to?: string
  has_anomaly_alert?: boolean
}
