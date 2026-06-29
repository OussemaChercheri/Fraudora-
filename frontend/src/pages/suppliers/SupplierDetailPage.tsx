import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getSupplierDetail, downloadSupplierReport } from '../../api/reports'
import { useAuthStore } from '../../store/authStore'

function formatTND(amount: number): string {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'TND', maximumFractionDigits: 2 }).format(amount)
}

function severityColor(severity: string): string {
  if (severity === 'HIGH') return '#dc2626'
  if (severity === 'MEDIUM') return '#ea580c'
  return '#6b7280'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    UPLOADED: 'Importée',
    PROCESSING: 'En cours',
    PROCESSED: 'Traitée',
    REVIEW_REQUIRED: 'Révision',
    ERROR: 'Erreur',
  }
  return map[status] || status
}

const STATUS_COLORS: Record<string, string> = {
  UPLOADED: '#6b7280',
  PROCESSING: '#3b82f6',
  PROCESSED: '#16a34a',
  REVIEW_REQUIRED: '#ea580c',
  ERROR: '#dc2626',
}

export default function SupplierDetailPage() {
  const { supplierName } = useParams<{ supplierName: string }>()
  const user = useAuthStore((state) => state.user)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [exporting, setExporting] = useState<'pdf' | 'excel' | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  const canExport = user && ['FINANCE', 'ADMIN'].includes(user.role)

  const { data, isLoading } = useQuery({
    queryKey: ['supplier-detail', supplierName, dateFrom, dateTo],
    queryFn: () => getSupplierDetail(supplierName!, dateFrom || undefined, dateTo || undefined),
    enabled: !!supplierName,
  })

  async function handleExport(format: 'pdf' | 'excel') {
    if (!supplierName) return
    setExporting(format)
    try {
      await downloadSupplierReport(supplierName, format, dateFrom || undefined, dateTo || undefined)
      setToast('Rapport téléchargé')
    } catch {
      setToast('Erreur lors du téléchargement')
    } finally {
      setExporting(null)
      setTimeout(() => setToast(null), 3000)
    }
  }

  if (isLoading) return <div className="page-container"><p>Chargement des détails fournisseur…</p></div>
  if (!data || 'error' in data) return <div className="page-container"><p className="form-error">Fournisseur introuvable ou accès refusé.</p></div>

  const riskColor = data.risk_level === 'Élevé' ? '#dc2626' : data.risk_level === 'Modéré' ? '#ea580c' : '#16a34a'

  return (
    <div className="page-container page-container--wide">
      <div className="page-header">
        <div>
          <h1>{data.supplier_name}</h1>
          <span
            className="severity-badge"
            style={{
              backgroundColor: riskColor,
              color: '#fff',
              padding: '4px 14px',
              borderRadius: '16px',
              fontSize: '14px',
              fontWeight: 600,
              display: 'inline-block',
            }}
          >
            {data.risk_score}/100 — {data.risk_level}
          </span>
        </div>
      </div>

      <div className="filters-bar">
        <div className="form-field">
          <label>Du</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </div>
        <div className="form-field">
          <label>Au</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </div>
        {canExport && (
          <>
            <button
              className="btn btn-primary btn-sm"
              disabled={exporting !== null}
              onClick={() => handleExport('pdf')}
            >
              {exporting === 'pdf' ? (
                <span className="btn-with-spinner"><span className="spinner spinner--sm" /> Export PDF…</span>
              ) : 'Export PDF'}
            </button>
            <button
              className="btn btn-primary btn-sm"
              disabled={exporting !== null}
              onClick={() => handleExport('excel')}
            >
              {exporting === 'excel' ? (
                <span className="btn-with-spinner"><span className="spinner spinner--sm" /> Export Excel…</span>
              ) : 'Export Excel'}
            </button>
          </>
        )}
      </div>

      {toast && <div className="form-success">{toast}</div>}

      <div className="dashboard-grid">
        <div className="metric-card">
          <span className="metric-card__label">Total</span>
          <span className="metric-card__value">{formatTND(data.total_sum)}</span>
        </div>
        <div className="metric-card">
          <span className="metric-card__label">Moyenne</span>
          <span className="metric-card__value">{formatTND(data.avg_amount)}</span>
        </div>
        <div className="metric-card">
          <span className="metric-card__label">Min</span>
          <span className="metric-card__value">{formatTND(data.min_amount)}</span>
        </div>
        <div className="metric-card">
          <span className="metric-card__label">Max</span>
          <span className="metric-card__value">{formatTND(data.max_amount)}</span>
        </div>
        <div className="metric-card">
          <span className="metric-card__label">Écart-type</span>
          <span className="metric-card__value">{formatTND(data.std_amount)}</span>
        </div>
      </div>

      <div className="analysis-card" style={{ marginTop: '20px' }}>
        <h2>Fréquence</h2>
        <div className="dashboard-grid">
          <div className="metric-card">
            <span className="metric-card__label">Factures / mois</span>
            <span className="metric-card__value">{data.frequence.invoices_per_month.toFixed(2)}</span>
          </div>
          <div className="metric-card">
            <span className="metric-card__label">Jours moyens entre factures</span>
            <span className="metric-card__value">{data.frequence.avg_days_between_invoices ?? '—'}</span>
          </div>
        </div>
      </div>

      <div className="analysis-card" style={{ marginTop: '20px' }}>
        <h2>Historique des factures</h2>
        {data.historique.length === 0 && <p>Aucune facture pour cette période.</p>}
        {data.historique.length > 0 && (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>N° facture</th>
                  <th>Montant TTC</th>
                  <th>TVA</th>
                  <th>Statut</th>
                  <th>Alertes</th>
                </tr>
              </thead>
              <tbody>
                {data.historique.map((h) => (
                  <tr key={h.invoice_id}>
                    <td>{h.invoice_date}</td>
                    <td>
                      <Link to={`/invoices/${h.invoice_id}`} style={{ textDecoration: 'none', fontWeight: 500 }}>
                        {h.invoice_number || '—'}
                      </Link>
                    </td>
                    <td>{formatTND(h.total_amount)}</td>
                    <td>{formatTND(h.tax_amount)}</td>
                    <td>
                      <span
                        style={{
                          display: 'inline-block',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontWeight: 600,
                          color: '#fff',
                          backgroundColor: STATUS_COLORS[h.status] || '#6b7280',
                        }}
                      >
                        {statusLabel(h.status)}
                      </span>
                    </td>
                    <td>
                      {h.has_anomaly && <span title="Anomalie" style={{ color: '#ea580c', marginRight: 4 }}>⚠</span>}
                      {h.has_duplicate && <span title="Doublon" style={{ color: '#dc2626' }}>⚡</span>}
                      {!h.has_anomaly && !h.has_duplicate && '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="analysis-card" style={{ marginTop: '20px' }}>
        <h2>Anomalies liées</h2>
        {data.anomalies.length === 0 && <p>Aucune anomalie détectée.</p>}
        {data.anomalies.length > 0 && (
          <div className="anomaly-list">
            {data.anomalies.map((a) => (
              <div
                key={a.id}
                className="anomaly-card"
                style={{
                  borderLeft: `4px solid ${severityColor(a.severity)}`,
                  padding: '12px',
                  marginBottom: '8px',
                  backgroundColor: '#f9fafb',
                  borderRadius: '6px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600 }}>{a.alert_type}</span>
                  <span
                    className="severity-badge"
                    style={{
                      backgroundColor: severityColor(a.severity),
                      color: '#fff',
                      padding: '2px 10px',
                      borderRadius: '12px',
                      fontSize: '12px',
                      fontWeight: 600,
                    }}
                  >
                    {a.severity}
                  </span>
                </div>
                <p style={{ margin: '8px 0', fontSize: '14px' }}>{a.description}</p>
                <div style={{ fontSize: '12px', color: '#666' }}>
                  <span>Facture : {a.invoice_number || '—'}</span>
                  <span style={{ marginLeft: '16px' }}>Date : {a.invoice_date || a.created_at?.slice(0, 10)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
