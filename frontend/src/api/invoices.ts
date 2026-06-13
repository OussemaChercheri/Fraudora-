import type {
  BulkUploadResponse,
  GetInvoicesParams,
  InvoiceDataResponse,
  InvoiceDataUpdate,
  InvoiceDetailResponse,
  InvoiceListResponse,
  InvoiceResponse,
} from '../types/invoice'
import apiClient from './client'

export async function uploadInvoice(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<InvoiceResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await apiClient.post<InvoiceResponse>(
    '/api/v1/invoices/upload',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (event) => {
        if (event.total && onProgress) {
          onProgress(Math.round((event.loaded / event.total) * 100))
        }
      },
    },
  )
  return data
}

export async function uploadBulk(files: FileList | File[]): Promise<BulkUploadResponse> {
  const formData = new FormData()
  Array.from(files).forEach((file) => formData.append('files', file))

  const { data } = await apiClient.post<BulkUploadResponse>(
    '/api/v1/invoices/upload/bulk',
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

export async function getInvoices(
  params: GetInvoicesParams = {},
): Promise<InvoiceListResponse> {
  const { data } = await apiClient.get<InvoiceListResponse>('/api/v1/invoices/', {
    params,
  })
  return data
}

export async function getInvoiceById(id: string): Promise<InvoiceDetailResponse> {
  const { data } = await apiClient.get<InvoiceDetailResponse>(`/api/v1/invoices/${id}`)
  return data
}

export async function getInvoiceData(id: string): Promise<InvoiceDataResponse> {
  const { data } = await apiClient.get<InvoiceDataResponse>(
    `/api/v1/invoices/${id}/data`,
  )
  return data
}

export async function updateInvoiceData(
  id: string,
  payload: Partial<InvoiceDataUpdate>,
): Promise<InvoiceDataResponse> {
  const { data } = await apiClient.put<InvoiceDataResponse>(
    `/api/v1/invoices/${id}/data`,
    payload,
  )
  return data
}

export async function deleteInvoice(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/invoices/${id}`)
}

export async function reprocessInvoice(id: string): Promise<InvoiceResponse> {
  const { data } = await apiClient.post<InvoiceResponse>(
    `/api/v1/invoices/${id}/reprocess`,
  )
  return data
}
