import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { deleteInvoice, getInvoices } from '../../api/invoices'
import FileTypeBadge from '../../components/invoices/FileTypeBadge'
import StatusBadge from '../../components/invoices/StatusBadge'
import { useAuthStore } from '../../store/authStore'
import type { InvoiceStatus } from '../../types/invoice'

const STATUS_OPTIONS: Array<{ value: '' | InvoiceStatus; label: string }> = [
  { value: '', label: 'All statuses' },
  { value: 'UPLOADED', label: 'Uploaded' },
  { value: 'PROCESSING', label: 'Processing' },
  { value: 'PROCESSED', label: 'Processed' },
  { value: 'REVIEW_REQUIRED', label: 'Review required' },
  { value: 'ERROR', label: 'Error' },
]

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function InvoicesListPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)

  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<'' | InvoiceStatus>('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [search, setSearch] = useState('')
  const [anomalyFilter, setAnomalyFilter] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['invoices', page, statusFilter, dateFrom, dateTo, anomalyFilter],
    queryFn: () =>
      getInvoices({
        page,
        page_size: 20,
        status: statusFilter || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        has_anomaly_alert: anomalyFilter || undefined,
      }),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteInvoice,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['invoices'] }),
  })

  const filteredItems = useMemo(() => {
    if (!data?.items) return []
    if (!search.trim()) return data.items
    const term = search.toLowerCase()
    return data.items.filter((item) =>
      item.original_filename.toLowerCase().includes(term),
    )
  }, [data?.items, search])

  const canDelete = (userId: string) =>
    user?.role === 'ADMIN' || user?.id === userId

  const handleDelete = (id: string, filename: string) => {
    if (window.confirm(`Delete "${filename}"? This cannot be undone.`)) {
      deleteMutation.mutate(id)
    }
  }

  return (
    <div className="page-container page-container--wide">
      <div className="page-header">
        <h1>Invoices</h1>
        <Link to="/invoices/upload" className="btn btn-primary">
          Upload invoice
        </Link>
      </div>

      <div className="filters-bar">
        <div className="form-field">
          <label htmlFor="status">Status</label>
          <select
            id="status"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as '' | InvoiceStatus)
              setPage(1)
            }}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label htmlFor="date_from">From</label>
          <input
            id="date_from"
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value)
              setPage(1)
            }}
          />
        </div>
        <div className="form-field">
          <label htmlFor="date_to">To</label>
          <input
            id="date_to"
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value)
              setPage(1)
            }}
          />
        </div>
        <div className="form-field form-field--grow">
          <label htmlFor="search">Search filename</label>
          <input
            id="search"
            type="search"
            placeholder="Filter by filename…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="form-field form-field--toggle">
          <label htmlFor="anomaly_filter">
            <input
              id="anomaly_filter"
              type="checkbox"
              checked={anomalyFilter}
              onChange={(e) => {
                setAnomalyFilter(e.target.checked)
                setPage(1)
              }}
            />
            Anomalies uniquement
          </label>
        </div>
      </div>

      {isLoading && <p>Loading invoices…</p>}
      {isError && <p className="form-error">Failed to load invoices.</p>}

      {!isLoading && !isError && (
        <>
          <div className="table-wrapper">
            <table className="data-table data-table--clickable">
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Alert</th>
                  <th>Uploaded</th>
                  <th>Size</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((invoice) => (
                  <tr
                    key={invoice.id}
                    onClick={() => navigate(`/invoices/${invoice.id}`)}
                  >
                    <td>{invoice.original_filename}</td>
                    <td>
                      <FileTypeBadge fileType={invoice.file_type} />
                    </td>
                    <td>
                      <StatusBadge status={invoice.status} />
                    </td>
                    <td>
                      {invoice.has_anomaly_alert && (
                        <span className="alert-indicator" title="Anomalie détectée">⚠️</span>
                      )}
                    </td>
                    <td>{formatDate(invoice.created_at)}</td>
                    <td>{invoice.file_size_kb} KB</td>
                    <td>
                      {canDelete(invoice.user_id) && (
                        <button
                          type="button"
                          className="btn btn-danger btn-sm"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDelete(invoice.id, invoice.original_filename)
                          }}
                          disabled={deleteMutation.isPending}
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {filteredItems.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center' }}>
                      No invoices found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {data && (
            <div className="pagination">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </button>
              <span className="pagination__info">
                Page {data.page} of {Math.max(data.total_pages, 1)} ({data.total} total)
              </span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={page >= data.total_pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
