import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  getInvoiceById,
  getInvoiceData,
  reprocessInvoice,
  updateInvoiceData,
} from '../../api/invoices'
import AnomalyAlertBanner from '../../components/AnomalyAlertBanner'
import ConfidenceBar from '../../components/invoices/ConfidenceBar'
import FileTypeBadge from '../../components/invoices/FileTypeBadge'
import StatusBadge from '../../components/invoices/StatusBadge'
import { useAuthStore } from '../../store/authStore'
import type { InvoiceDataUpdate } from '../../types/invoice'

interface EditFormState {
  invoice_number: string
  invoice_date: string
  supplier_name: string
  total_amount: string
  tax_amount: string
}

function formatDateTime(dateString: string) {
  return new Date(dateString).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function toEditForm(data: Awaited<ReturnType<typeof getInvoiceData>>): EditFormState {
  return {
    invoice_number: data.invoice_number.value ?? '',
    invoice_date: data.invoice_date.value ?? '',
    supplier_name: data.supplier_name.value ?? '',
    total_amount: data.total_amount.value?.toString() ?? '',
    tax_amount: data.tax_amount.value?.toString() ?? '',
  }
}

function ExtractedField({
  label,
  value,
  confidence,
  needsReview,
}: {
  label: string
  value: string | null
  confidence: number
  needsReview: boolean
}) {
  return (
    <div className="extracted-field">
      <div className="extracted-field__value">
        <span className="extracted-field__label">{label}</span>
        <span>{value ?? '—'}</span>
      </div>
      <ConfidenceBar confidence={confidence} needsReview={needsReview} />
    </div>
  )
}

export default function InvoiceDetailPage() {
  const { id = '' } = useParams()
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const canEdit = user && ['ADMIN', 'FINANCE', 'COMPTABLE'].includes(user.role)

  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState<EditFormState>({
    invoice_number: '',
    invoice_date: '',
    supplier_name: '',
    total_amount: '',
    tax_amount: '',
  })
  const [showRawOcr, setShowRawOcr] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const invoiceQuery = useQuery({
    queryKey: ['invoice', id],
    queryFn: () => getInvoiceById(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'UPLOADED' || status === 'PROCESSING') return 3000
      return false
    },
  })

  const dataQuery = useQuery({
    queryKey: ['invoice-data', id],
    queryFn: () => getInvoiceData(id),
    enabled: !!id && !!invoiceQuery.data && invoiceQuery.data.status !== 'UPLOADED',
    retry: (failureCount, error) => {
      if ((error as { response?: { status?: number } })?.response?.status === 404) {
        return failureCount < 10
      }
      return failureCount < 2
    },
    refetchInterval: () => {
      const invoiceStatus = invoiceQuery.data?.status
      if (invoiceStatus === 'PROCESSING') return 3000
      return false
    },
  })

  useEffect(() => {
    if (dataQuery.data) {
      setEditForm(toEditForm(dataQuery.data))
    }
  }, [dataQuery.data])

  const updateMutation = useMutation({
    mutationFn: (payload: Partial<InvoiceDataUpdate>) =>
      updateInvoiceData(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoice-data', id] })
      queryClient.invalidateQueries({ queryKey: ['invoice', id] })
      setIsEditing(false)
      setSaveError(null)
    },
    onError: () => setSaveError('Failed to save changes.'),
  })

  const reprocessMutation = useMutation({
    mutationFn: () => reprocessInvoice(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoice', id] })
      queryClient.invalidateQueries({ queryKey: ['invoice-data', id] })
    },
  })

  const invoice = invoiceQuery.data
  const invoiceData = dataQuery.data

  const canReprocess =
    invoice?.status === 'ERROR' || invoice?.status === 'REVIEW_REQUIRED'

  const startEditing = () => {
    if (invoiceData) setEditForm(toEditForm(invoiceData))
    setIsEditing(true)
    setSaveError(null)
  }

  const cancelEditing = () => {
    if (invoiceData) setEditForm(toEditForm(invoiceData))
    setIsEditing(false)
    setSaveError(null)
  }

  const saveChanges = () => {
    const payload: Partial<InvoiceDataUpdate> = {}

    if (editForm.invoice_number !== (invoiceData?.invoice_number.value ?? '')) {
      payload.invoice_number = editForm.invoice_number
    }
    if (editForm.invoice_date !== (invoiceData?.invoice_date.value ?? '')) {
      payload.invoice_date = editForm.invoice_date || undefined
    }
    if (editForm.supplier_name !== (invoiceData?.supplier_name.value ?? '')) {
      payload.supplier_name = editForm.supplier_name
    }
    const total = editForm.total_amount ? parseFloat(editForm.total_amount) : undefined
    const tax = editForm.tax_amount ? parseFloat(editForm.tax_amount) : undefined
    if (total !== invoiceData?.total_amount.value) payload.total_amount = total
    if (tax !== invoiceData?.tax_amount.value) payload.tax_amount = tax

    if (Object.keys(payload).length === 0) {
      setIsEditing(false)
      return
    }

    updateMutation.mutate(payload)
  }

  if (invoiceQuery.isLoading) return <div className="page-container">Loading…</div>
  if (invoiceQuery.isError || !invoice) {
    return (
      <div className="page-container">
        <p className="form-error">Invoice not found.</p>
        <Link to="/invoices" className="link link--inline">
          Back to invoices
        </Link>
      </div>
    )
  }

  return (
    <div className="page-container page-container--wide">
      <Link to="/invoices" className="link link--inline back-link">
        ← Back to invoices
      </Link>

      {invoice.status === 'REVIEW_REQUIRED' && (
        <div className="alert alert--warning">
          Some fields need manual review before this invoice can be marked as processed.
        </div>
      )}

      {invoice.has_anomaly_alert && <AnomalyAlertBanner invoiceId={id} />}

      <div className="detail-header">
        <div>
          <h1>{invoice.original_filename}</h1>
          <div className="detail-header__meta">
            <StatusBadge status={invoice.status} />
            <FileTypeBadge fileType={invoice.file_type} />
            <span>{formatDateTime(invoice.created_at)}</span>
            <span>{invoice.file_size_kb} KB</span>
          </div>
        </div>
        {canReprocess && (
          <button
            type="button"
            className="btn btn-secondary"
            disabled={reprocessMutation.isPending || invoice.status === 'PROCESSING'}
            onClick={() => reprocessMutation.mutate()}
          >
            {reprocessMutation.isPending ? (
              <span className="btn-with-spinner">
                <span className="spinner spinner--sm" />
                Relance…
              </span>
            ) : (
              "Relancer l'OCR"
            )}
          </button>
        )}
      </div>

      <section className="detail-card">
        <div className="detail-card__header">
          <h2>Extracted data</h2>
          {!isEditing && invoiceData && canEdit && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={startEditing}
            >
              Edit
            </button>
          )}
        </div>

        {invoice.status === 'PROCESSING' && (
          <div className="ocr-spinner">
            <div className="spinner" />
            <span>Processing OCR…</span>
          </div>
        )}

        {dataQuery.isLoading && invoice.status !== 'PROCESSING' && (
          <p>Loading extracted data…</p>
        )}

        {dataQuery.isError && invoice.status !== 'UPLOADED' && (
          <p className="form-error">Extracted data not available yet.</p>
        )}

        {invoiceData && !isEditing && (
          <div className="extracted-fields">
            <ExtractedField
              label="Invoice number"
              value={invoiceData.invoice_number.value}
              confidence={invoiceData.invoice_number.confidence}
              needsReview={invoiceData.invoice_number.needs_review}
            />
            <ExtractedField
              label="Invoice date"
              value={invoiceData.invoice_date.value}
              confidence={invoiceData.invoice_date.confidence}
              needsReview={invoiceData.invoice_date.needs_review}
            />
            <ExtractedField
              label="Supplier name"
              value={invoiceData.supplier_name.value}
              confidence={invoiceData.supplier_name.confidence}
              needsReview={invoiceData.supplier_name.needs_review}
            />
            <ExtractedField
              label="Total amount"
              value={invoiceData.total_amount.value?.toString() ?? null}
              confidence={invoiceData.total_amount.confidence}
              needsReview={invoiceData.total_amount.needs_review}
            />
            <ExtractedField
              label="Tax amount (TVA)"
              value={invoiceData.tax_amount.value?.toString() ?? null}
              confidence={invoiceData.tax_amount.confidence}
              needsReview={invoiceData.tax_amount.needs_review}
            />
          </div>
        )}

        {invoiceData && isEditing && (
          <div className="extracted-fields extracted-fields--edit">
            {saveError && <div className="form-error">{saveError}</div>}
            <div className="form-field">
              <label htmlFor="invoice_number">Invoice number</label>
              <input
                id="invoice_number"
                value={editForm.invoice_number}
                onChange={(e) =>
                  setEditForm((f) => ({ ...f, invoice_number: e.target.value }))
                }
              />
            </div>
            <div className="form-field">
              <label htmlFor="invoice_date">Invoice date</label>
              <input
                id="invoice_date"
                type="date"
                value={editForm.invoice_date}
                onChange={(e) =>
                  setEditForm((f) => ({ ...f, invoice_date: e.target.value }))
                }
              />
            </div>
            <div className="form-field">
              <label htmlFor="supplier_name">Supplier name</label>
              <input
                id="supplier_name"
                value={editForm.supplier_name}
                onChange={(e) =>
                  setEditForm((f) => ({ ...f, supplier_name: e.target.value }))
                }
              />
            </div>
            <div className="form-field">
              <label htmlFor="total_amount">Total amount</label>
              <input
                id="total_amount"
                type="number"
                min="0"
                step="0.001"
                value={editForm.total_amount}
                onChange={(e) =>
                  setEditForm((f) => ({ ...f, total_amount: e.target.value }))
                }
              />
            </div>
            <div className="form-field">
              <label htmlFor="tax_amount">Tax amount (TVA)</label>
              <input
                id="tax_amount"
                type="number"
                min="0"
                step="0.001"
                value={editForm.tax_amount}
                onChange={(e) =>
                  setEditForm((f) => ({ ...f, tax_amount: e.target.value }))
                }
              />
            </div>
            <div className="modal-actions">
              <button type="button" className="btn btn-secondary" onClick={cancelEditing}>
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={updateMutation.isPending}
                onClick={saveChanges}
              >
                {updateMutation.isPending ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        )}
      </section>

      {invoice.ocr_raw_text && (
        <section className="detail-card">
          <button
            type="button"
            className="collapsible-header"
            onClick={() => setShowRawOcr((v) => !v)}
          >
            <span>Raw OCR text</span>
            <span>{showRawOcr ? '▲' : '▼'}</span>
          </button>
          {showRawOcr && (
            <pre className="ocr-raw-text">{invoice.ocr_raw_text}</pre>
          )}
        </section>
      )}
    </div>
  )
}
