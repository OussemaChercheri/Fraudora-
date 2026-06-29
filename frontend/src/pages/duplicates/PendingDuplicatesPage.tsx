import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getDuplicatesReportSummary, downloadDuplicatesReport } from '../../api/reports'
import { useAuthStore } from '../../store/authStore'

function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

function daysAgoISO(n: number) {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

function formatTND(amount: number): string {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'TND', maximumFractionDigits: 2 }).format(amount)
}

export default function PendingDuplicatesPage() {
  const user = useAuthStore((state) => state.user)
  const [dateFrom, setDateFrom] = useState(daysAgoISO(30))
  const [dateTo, setDateTo] = useState(todayISO())
  const [exporting, setExporting] = useState<'pdf' | 'excel' | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  const canExport = user && ['FINANCE', 'ADMIN'].includes(user.role)

  const { data, isLoading } = useQuery({
    queryKey: ['duplicates-report-summary', dateFrom, dateTo],
    queryFn: () => getDuplicatesReportSummary(dateFrom, dateTo),
    enabled: !!canExport,
  })

  async function handleExport(format: 'pdf' | 'excel') {
    setExporting(format)
    try {
      await downloadDuplicatesReport(format, dateFrom, dateTo)
      setToast('Rapport téléchargé')
    } catch {
      setToast('Erreur lors du téléchargement')
    } finally {
      setExporting(null)
      setTimeout(() => setToast(null), 3000)
    }
  }

  return (
    <div className="page-container page-container--wide">
      <div className="page-header">
        <h1>Doublons</h1>
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

      {isLoading && <p>Chargement des statistiques…</p>}

      {data && (
        <div className="dashboard-grid" style={{ marginBottom: '24px' }}>
          <div className="metric-card">
            <span className="metric-card__label">Taux de doublon</span>
            <span className="metric-card__value">{data.duplicate_rate}%</span>
          </div>
          <div className="metric-card" style={{ borderLeft: '4px solid var(--status-error, #dc2626)' }}>
            <span className="metric-card__label">Montant à risque total</span>
            <span className="metric-card__value">{formatTND(data.montant_a_risque_total)}</span>
          </div>
          <div className="metric-card">
            <span className="metric-card__label">Confirmés</span>
            <span className="metric-card__value">{data.confirmed_count}</span>
          </div>
          <div className="metric-card">
            <span className="metric-card__label">En attente</span>
            <span className="metric-card__value">{data.pending_count}</span>
          </div>
        </div>
      )}

      <div className="analysis-card">
        <h2>Correspondances en attente</h2>
        {(!data || data.details.length === 0) && <p>Aucun doublon détecté sur cette période.</p>}
        {data && data.details.length > 0 && (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Facture</th>
                  <th>Fournisseur</th>
                  <th>Montant</th>
                  <th>Date</th>
                  <th>Source</th>
                  <th>Similarité</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {data.details.map((d: any, i: number) => (
                  <tr key={i} style={d.status === 'CONFIRMED_DUPLICATE' ? { backgroundColor: '#FEE2E2' } : d.status === 'PENDING' ? { backgroundColor: '#FEF3C7' } : undefined}>
                    <td>{d.invoice_filename}</td>
                    <td>{d.supplier_name}</td>
                    <td>{d.total_amount.toFixed(2)}</td>
                    <td>{d.invoice_date}</td>
                    <td>{d.matched_invoice_filename}</td>
                    <td>{d.similarity_score}</td>
                    <td>{d.status === 'CONFIRMED_DUPLICATE' ? 'Confirmé' : d.status === 'PENDING' ? 'En attente' : d.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
