import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getDashboardSummary } from '../api/dashboard'
import type { DashboardSummary } from '../types/dashboard'
import { useAuthStore } from '../store/authStore'

function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

function daysAgoISO(n: number) {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

const STATUS_COLORS: Record<string, string> = {
  UPLOADED: 'var(--status-uploaded, #6b7280)',
  PROCESSING: 'var(--status-processing, #3b82f6)',
  PROCESSED: 'var(--status-processed, #16a34a)',
  REVIEW_REQUIRED: 'var(--status-review, #ea580c)',
  ERROR: 'var(--status-error, #dc2626)',
}

const STATUS_LABELS: Record<string, string> = {
  UPLOADED: 'Importée',
  PROCESSING: 'En cours',
  PROCESSED: 'Traitée',
  REVIEW_REQUIRED: 'Révision',
  ERROR: 'Erreur',
}

function formatTND(amount: number): string {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'TND', maximumFractionDigits: 2 }).format(amount)
}

function riskScoreColor(score: number): string {
  if (score >= 60) return 'var(--confidence-low, #dc2626)'
  if (score >= 30) return 'var(--confidence-mid, #ea580c)'
  return 'var(--confidence-high, #16a34a)'
}

function MetricCard({ label, value, unit, accent }: { label: string; value: string | number; unit?: string; accent?: string }) {
  return (
    <div className="metric-card" style={accent ? { borderLeft: `4px solid ${accent}` } : undefined}>
      <span className="metric-card__label">{label}</span>
      <span className="metric-card__value">{value}{unit && <small>{unit}</small>}</span>
    </div>
  )
}

interface DateFilterProps {
  dateFrom: string
  dateTo: string
  onChange: (from: string, to: string) => void
}

function DateFilter({ dateFrom, dateTo, onChange }: DateFilterProps) {
  const presets = [
    { label: '7 jours', days: 7 },
    { label: '30 jours', days: 30 },
    { label: '90 jours', days: 90 },
    { label: 'Cette année', days: 365 },
  ]
  return (
    <div className="filters-bar dashboard-filters">
      <div className="form-field form-field--grow">
        <label>Du</label>
        <input type="date" value={dateFrom} onChange={(e) => onChange(e.target.value, dateTo)} />
      </div>
      <div className="form-field form-field--grow">
        <label>Au</label>
        <input type="date" value={dateTo} onChange={(e) => onChange(dateFrom, e.target.value)} />
      </div>
      {presets.map((p) => (
        <button
          key={p.label}
          className="btn btn-secondary btn-sm"
          onClick={() => onChange(daysAgoISO(p.days), todayISO())}
        >
          {p.label}
        </button>
      ))}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className="status-badge--small"
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '12px',
        fontWeight: 600,
        color: '#fff',
        backgroundColor: STATUS_COLORS[status] || '#6b7280',
      }}
    >
      {STATUS_LABELS[status] || status}
    </span>
  )
}

function EvolutionChart({ data }: { data: DashboardSummary['evolution'] }) {
  const maxVal = Math.max(1, ...data.uploaded, ...data.processed)
  return (
    <div className="monthly-bars">
      {data.labels.length === 0 && <p style={{ color: 'var(--text-h, #666)', fontSize: '14px' }}>Aucune donnée</p>}
      {data.labels.map((label, i) => {
        const uploaded = data.uploaded[i] ?? 0
        const processed = data.processed[i] ?? 0
        return (
          <div key={label} className="monthly-bar-row">
            <span className="monthly-bar-row__label" style={{ fontSize: '11px' }}>{label.slice(5)}</span>
            <div className="monthly-bar-row__track">
              <div
                className="monthly-bar-row__fill"
                style={{ width: `${(uploaded / maxVal) * 100}%`, backgroundColor: '#3b82f6' }}
              />
            </div>
            <div className="monthly-bar-row__track">
              <div
                className="monthly-bar-row__fill"
                style={{ width: `${(processed / maxVal) * 100}%`, backgroundColor: '#16a34a' }}
              />
            </div>
            <span className="monthly-bar-row__count">{uploaded}/{processed}</span>
          </div>
        )
      })}
      <div style={{ display: 'flex', gap: '16px', justifyContent: 'flex-end', fontSize: '12px', color: 'var(--text-h, #666)', marginTop: '8px' }}>
        <span><span style={{ display: 'inline-block', width: 10, height: 10, backgroundColor: '#3b82f6', borderRadius: 2, marginRight: 4 }} /> Importées</span>
        <span><span style={{ display: 'inline-block', width: 10, height: 10, backgroundColor: '#16a34a', borderRadius: 2, marginRight: 4 }} /> Traitées</span>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user)
  const [dateFrom, setDateFrom] = useState(daysAgoISO(30))
  const [dateTo, setDateTo] = useState(todayISO())

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard', dateFrom, dateTo],
    queryFn: () => getDashboardSummary(dateFrom, dateTo),
  })

  return (
    <div className="page-container page-container--wide">
      <div className="page-header">
        <h1>Dashboard</h1>
      </div>

      <DateFilter
        dateFrom={dateFrom}
        dateTo={dateTo}
        onChange={(from, to) => { setDateFrom(from); setDateTo(to) }}
      />

      {isLoading && <p>Chargement du tableau de bord...</p>}
      {!isLoading && data && (
        <div className="dashboard-grid">
          <div className="analysis-card">
            <h2>Factures totales</h2>
            <div className="analysis-row analysis-row--metrics">
              <MetricCard label="Total" value={data.factures_totales.total} />
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '12px' }}>
              {Object.entries(data.factures_totales.by_status).map(([status, count]) => (
                <StatusBadge key={status} status={status} />
              ))}
            </div>
          </div>

          <Link to="/duplicates" className="analysis-card" style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}>
            <h2>Alertes en attente</h2>
            <div className="analysis-row analysis-row--metrics">
              <MetricCard label="Doublons" value={data.alertes.pending_duplicates} />
              <MetricCard label="Anomalies" value={data.alertes.pending_anomalies} />
            </div>
          </Link>

          <Link to="/anomalies" className="analysis-card" style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer', borderLeft: data.suspectes.count > 0 ? '4px solid var(--status-review, #ea580c)' : undefined }}>
            <h2>Factures suspectes</h2>
            <div className="analysis-row analysis-row--metrics">
              <MetricCard
                label="Suspectes"
                value={data.suspectes.count}
                accent={data.suspectes.count > 0 ? 'var(--status-review, #ea580c)' : undefined}
              />
            </div>
          </Link>

          <div className="analysis-card analysis-card--full">
            <h2>Évolution</h2>
            <EvolutionChart data={data.evolution} />
          </div>

          <div className="analysis-card">
            <h2>Top fournisseurs</h2>
            {data.top_fournisseurs.items.length === 0 && <p style={{ color: 'var(--text-h, #666)', fontSize: '14px' }}>Aucune donnée</p>}
            <div className="supplier-rank-list">
              {data.top_fournisseurs.items.map((s, i) => (
                <div key={s.supplier_name} className="supplier-rank-item">
                  <span className="supplier-rank-item__rank">{i + 1}</span>
                  <span className="supplier-rank-item__name">{s.supplier_name}</span>
                  <span className="supplier-rank-item__count">{s.invoice_count} fact.</span>
                  <span className="supplier-rank-item__amount">{formatTND(s.total_amount_sum)}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="analysis-card">
            <h2>Scores de risque</h2>
            {data.risques.items.length === 0 && <p style={{ color: 'var(--text-h, #666)', fontSize: '14px' }}>Aucun fournisseur évalué</p>}
            <div className="supplier-rank-list">
              {data.risques.items.map((s) => (
                <Link key={s.supplier_name} to="/anomalies/suppliers" style={{ textDecoration: 'none', color: 'inherit' }}>
                  <div className="supplier-rank-item">
                    <span className="supplier-rank-item__name">{s.supplier_name}</span>
                    <span
                      className="supplier-rank-item__risk"
                      style={{
                        backgroundColor: riskScoreColor(s.risk_score),
                        color: '#fff',
                        padding: '2px 10px',
                        borderRadius: '12px',
                        fontSize: '13px',
                        fontWeight: 600,
                      }}
                    >
                      {s.risk_score}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
