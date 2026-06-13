import { useQueries, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import {
  downloadReportExcel,
  downloadReportPdf,
  getMonthlyVolume,
  getOcrQualityStats,
  getProcessingSummary,
  getSupplierSummary,
} from '../../api/analysis'
import { getInvoiceData, getInvoices } from '../../api/invoices'
import { useAuthStore } from '../../store/authStore'
import {
  OCR_FIELD_KEYS,
  OCR_FIELD_LABELS,
} from '../../types/analysis'
import type { InvoiceDataResponse } from '../../types/invoice'

function confidenceBarColor(percent: number): string {
  if (percent >= 80) return 'var(--confidence-high, #16a34a)'
  if (percent >= 50) return 'var(--confidence-mid, #ea580c)'
  return 'var(--confidence-low, #dc2626)'
}

function getMissingFields(data: InvoiceDataResponse): string[] {
  const fields = [
    { label: OCR_FIELD_LABELS.invoice_number, confidence: data.invoice_number.confidence },
    { label: OCR_FIELD_LABELS.invoice_date, confidence: data.invoice_date.confidence },
    { label: OCR_FIELD_LABELS.supplier_name, confidence: data.supplier_name.confidence },
    { label: OCR_FIELD_LABELS.total_amount, confidence: data.total_amount.confidence },
    { label: OCR_FIELD_LABELS.tax_amount, confidence: data.tax_amount.confidence },
  ]
  return fields.filter((item) => item.confidence < 0.5).map((item) => item.label)
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric-card">
      <span className="metric-card__label">{label}</span>
      <span className="metric-card__value">{value}</span>
    </div>
  )
}

export default function AnalysisDashboardPage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const canExport = user && ['FINANCE', 'ADMIN'].includes(user.role)

  const [downloadingPdf, setDownloadingPdf] = useState(false)
  const [downloadingExcel, setDownloadingExcel] = useState(false)

  const summaryQuery = useQuery({
    queryKey: ['analysis', 'summary'],
    queryFn: getProcessingSummary,
  })

  const ocrQuery = useQuery({
    queryKey: ['analysis', 'ocr-quality'],
    queryFn: getOcrQualityStats,
  })

  const suppliersQuery = useQuery({
    queryKey: ['analysis', 'suppliers'],
    queryFn: getSupplierSummary,
  })

  const monthlyQuery = useQuery({
    queryKey: ['analysis', 'monthly-volume'],
    queryFn: () => getMonthlyVolume(6),
  })

  const reviewInvoicesQuery = useQuery({
    queryKey: ['invoices', 'REVIEW_REQUIRED'],
    queryFn: () => getInvoices({ status: 'REVIEW_REQUIRED', page_size: 100 }),
  })

  const reviewItems = reviewInvoicesQuery.data?.items ?? []

  const reviewDataQueries = useQueries({
    queries: reviewItems.map((invoice) => ({
      queryKey: ['invoice-data', invoice.id],
      queryFn: () => getInvoiceData(invoice.id),
      enabled: !!invoice.id,
    })),
  })

  const maxMonthlyCount = Math.max(
    ...(monthlyQuery.data?.map((item) => item.count) ?? [1]),
    1,
  )

  const topSuppliers = (suppliersQuery.data ?? []).slice(0, 10)

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true)
    try {
      await downloadReportPdf()
    } finally {
      setDownloadingPdf(false)
    }
  }

  const handleDownloadExcel = async () => {
    setDownloadingExcel(true)
    try {
      await downloadReportExcel()
    } finally {
      setDownloadingExcel(false)
    }
  }

  return (
    <div className="page-container page-container--wide analysis-dashboard">
      <div className="page-header">
        <h1>Analyse OCR</h1>
        <Link to="/invoices" className="link link--inline">
          Voir les factures
        </Link>
      </div>

      <div className="analysis-grid">
        <div className="analysis-row analysis-row--metrics">
          {summaryQuery.isLoading && <p>Chargement des indicateurs…</p>}
          {summaryQuery.data && (
            <>
              <MetricCard
                label="Total factures"
                value={summaryQuery.data.total_invoices}
              />
              <MetricCard
                label="Taux traité"
                value={`${summaryQuery.data.processed_rate}%`}
              />
              <MetricCard
                label="Révision requise"
                value={`${summaryQuery.data.review_required_rate}%`}
              />
              <MetricCard
                label="Taux d'erreur"
                value={`${summaryQuery.data.error_rate}%`}
              />
            </>
          )}
        </div>

        <div className="analysis-card analysis-card--full">
          <h2>Qualité OCR</h2>
          {ocrQuery.isLoading && <p>Chargement…</p>}
          {ocrQuery.data && (
            <div className="ocr-quality-list">
              {OCR_FIELD_KEYS.map((fieldKey) => {
                const confidence = ocrQuery.data.avg_confidence[fieldKey] ?? 0
                const extractionRate =
                  ocrQuery.data.field_extraction_rate[fieldKey] ?? 0
                const percent = Math.round(confidence * 100)
                return (
                  <div key={fieldKey} className="ocr-quality-item">
                    <div className="ocr-quality-item__header">
                      <span className="ocr-quality-item__label">
                        {OCR_FIELD_LABELS[fieldKey]}
                        <span className="extraction-badge">
                          {extractionRate}% extraits
                        </span>
                      </span>
                      <span className="ocr-quality-item__percent">{percent}%</span>
                    </div>
                    <div className="confidence-bar__track">
                      <div
                        className="confidence-bar__fill"
                        style={{
                          width: `${percent}%`,
                          backgroundColor: confidenceBarColor(percent),
                        }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="analysis-row analysis-row--split">
          <div className="analysis-card">
            <h2>Volume mensuel</h2>
            {monthlyQuery.isLoading && <p>Chargement…</p>}
            {monthlyQuery.data && (
              <div className="monthly-bars">
                {monthlyQuery.data.map((item) => {
                  const uploadWidth = (item.count / maxMonthlyCount) * 100
                  const processedRatio =
                    item.count > 0 ? (item.processed_count / item.count) * 100 : 0
                  return (
                    <div key={item.month} className="monthly-bar-row">
                      <span className="monthly-bar-row__label">{item.month}</span>
                      <div className="monthly-bar-row__track">
                        <div
                          className="monthly-bar-row__fill"
                          style={{
                            width: `${uploadWidth}%`,
                            background: `linear-gradient(to right, #185FA5 ${processedRatio}%, #94a3b8 ${processedRatio}%)`,
                          }}
                        />
                      </div>
                      <span className="monthly-bar-row__count">
                        {item.processed_count}/{item.count}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          <div className="analysis-card">
            <h2>Top fournisseurs</h2>
            {suppliersQuery.isLoading && <p>Chargement…</p>}
            {topSuppliers.length === 0 && !suppliersQuery.isLoading && (
              <p>Aucun fournisseur disponible.</p>
            )}
            <ol className="supplier-rank-list">
              {topSuppliers.map((supplier, index) => (
                <li key={supplier.supplier_name} className="supplier-rank-item">
                  <span className="supplier-rank-item__rank">{index + 1}</span>
                  <span className="supplier-rank-item__name">
                    {supplier.supplier_name}
                  </span>
                  <span className="supplier-rank-item__badge">
                    {supplier.invoice_count}
                  </span>
                  <span className="supplier-rank-item__amount">
                    {supplier.total_amount_sum.toFixed(2)}
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </div>

        <div className="analysis-card analysis-card--full">
          <h2>Factures à réviser</h2>
          {reviewInvoicesQuery.isLoading && <p>Chargement…</p>}
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Fichier</th>
                  <th>Date upload</th>
                  <th>Champs manquants</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {reviewItems.map((invoice, index) => {
                  const dataQuery = reviewDataQueries[index]
                  const missing = dataQuery.data
                    ? getMissingFields(dataQuery.data)
                    : dataQuery.isLoading
                      ? ['…']
                      : ['—']
                  return (
                    <tr key={invoice.id}>
                      <td>
                        <Link to={`/invoices/${invoice.id}`} className="link link--inline">
                          {invoice.original_filename}
                        </Link>
                      </td>
                      <td>{formatDate(invoice.created_at)}</td>
                      <td>{missing.join(', ')}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          onClick={() => navigate(`/invoices/${invoice.id}`)}
                        >
                          Corriger
                        </button>
                      </td>
                    </tr>
                  )
                })}
                {reviewItems.length === 0 && !reviewInvoicesQuery.isLoading && (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center' }}>
                      Aucune facture à réviser.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {canExport && (
          <div className="analysis-card analysis-card--full analysis-export">
            <h2>Exporter le rapport</h2>
            <div className="analysis-export__actions">
              <button
                type="button"
                className="btn btn-primary"
                disabled={downloadingPdf}
                onClick={handleDownloadPdf}
              >
                {downloadingPdf ? (
                  <span className="btn-with-spinner">
                    <span className="spinner spinner--sm" />
                    Téléchargement…
                  </span>
                ) : (
                  'Télécharger PDF'
                )}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={downloadingExcel}
                onClick={handleDownloadExcel}
              >
                {downloadingExcel ? (
                  <span className="btn-with-spinner">
                    <span className="spinner spinner--sm" />
                    Téléchargement…
                  </span>
                ) : (
                  'Télécharger Excel'
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
