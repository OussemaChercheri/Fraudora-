import type {
  MonthlyVolumeItem,
  OcrQualityStats,
  ProcessingSummary,
  SupplierSummaryItem,
} from '../types/analysis'
import apiClient from './client'

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export async function getProcessingSummary(): Promise<ProcessingSummary> {
  const { data } = await apiClient.get<ProcessingSummary>('/api/v1/analysis/summary')
  return data
}

export async function getOcrQualityStats(): Promise<OcrQualityStats> {
  const { data } = await apiClient.get<OcrQualityStats>('/api/v1/analysis/ocr-quality')
  return data
}

export async function getSupplierSummary(): Promise<SupplierSummaryItem[]> {
  const { data } = await apiClient.get<SupplierSummaryItem[]>('/api/v1/analysis/suppliers')
  return data
}

export async function getMonthlyVolume(months = 6): Promise<MonthlyVolumeItem[]> {
  const { data } = await apiClient.get<MonthlyVolumeItem[]>(
    '/api/v1/analysis/monthly-volume',
    { params: { months } },
  )
  return data
}

export async function downloadReportPdf(): Promise<void> {
  const response = await apiClient.get('/api/v1/analysis/report/pdf', {
    responseType: 'blob',
  })
  const blob = response.data as Blob
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  triggerBlobDownload(blob, `fraudguard_rapport_${date}.pdf`)
}

export async function downloadReportExcel(): Promise<void> {
  const response = await apiClient.get('/api/v1/analysis/report/excel', {
    responseType: 'blob',
  })
  const blob = response.data as Blob
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  triggerBlobDownload(blob, `fraudguard_rapport_${date}.xlsx`)
}
