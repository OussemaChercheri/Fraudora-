import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getExpenseEvolution } from '../../api/reports'

function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

function monthsAgoISO(n: number) {
  const d = new Date()
  d.setMonth(d.getMonth() - n)
  return d.toISOString().slice(0, 10)
}

function formatTND(amount: number): string {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'TND', maximumFractionDigits: 2 }).format(amount)
}

export default function ExpenseEvolutionPage() {
  const [dateFrom, setDateFrom] = useState(monthsAgoISO(3))
  const [dateTo, setDateTo] = useState(todayISO())
  const [granularity, setGranularity] = useState('month')

  const { data, isLoading } = useQuery({
    queryKey: ['expense-evolution', dateFrom, dateTo, granularity],
    queryFn: () => getExpenseEvolution(dateFrom, dateTo, granularity),
  })

  const maxAmount = Math.max(
    ...(data?.period_n.buckets.map((b) => b.amount) ?? []),
    ...(data?.period_n_minus_1.buckets.map((b) => b.amount) ?? []),
    1,
  )

  return (
    <div className="page-container page-container--wide">
      <div className="page-header">
        <h1>Évolution des dépenses</h1>
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
        <div className="form-field">
          <label>Granularité</label>
          <select value={granularity} onChange={(e) => setGranularity(e.target.value)}>
            <option value="day">Jour</option>
            <option value="week">Semaine</option>
            <option value="month">Mois</option>
          </select>
        </div>
      </div>

      {isLoading && <p>Chargement de l'évolution des dépenses…</p>}

      {data && (
        <>
          <div className="dashboard-grid">
            <div className="metric-card">
              <span className="metric-card__label">Période actuelle</span>
              <span className="metric-card__value">{formatTND(data.period_n.total)}</span>
              <small style={{ color: '#666', fontSize: '12px' }}>{data.period_n.label}</small>
            </div>
            <div className="metric-card">
              <span className="metric-card__label">Période précédente</span>
              <span className="metric-card__value">{formatTND(data.period_n_minus_1.total)}</span>
              <small style={{ color: '#666', fontSize: '12px' }}>{data.period_n_minus_1.label}</small>
            </div>
            <div className="metric-card">
              <span className="metric-card__label">Variation</span>
              <span
                className="metric-card__value"
                style={{
                  color: data.variation_direction === 'hausse' ? '#dc2626' : data.variation_direction === 'baisse' ? '#16a34a' : '#6b7280',
                }}
              >
                {data.variation_pct > 999 ? '>999%' : `${data.variation_pct}%`}
                <span style={{ marginLeft: 4 }}>
                  {data.variation_direction === 'hausse' ? '↑' : data.variation_direction === 'baisse' ? '↓' : '→'}
                </span>
              </span>
              <small style={{ color: '#666', fontSize: '12px' }}>
                {data.variation_direction === 'hausse' ? 'Hausse' : data.variation_direction === 'baisse' ? 'Baisse' : 'Stable'}
              </small>
            </div>
          </div>

          <div className="analysis-card" style={{ marginTop: '20px' }}>
            <h2>Comparaison par période</h2>
            <div style={{ display: 'flex', gap: '16px', justifyContent: 'flex-end', fontSize: '12px', color: '#666', marginBottom: '12px' }}>
              <span><span style={{ display: 'inline-block', width: 12, height: 12, backgroundColor: '#3b82f6', borderRadius: 2, marginRight: 4 }} /> Période actuelle</span>
              <span><span style={{ display: 'inline-block', width: 12, height: 12, backgroundColor: '#9ca3af', borderRadius: 2, marginRight: 4 }} /> Période précédente</span>
            </div>
            <div className="monthly-bars">
              {data.period_n.buckets.map((bucket, i) => {
                const prevBucket = data.period_n_minus_1.buckets[i]
                const prevAmount = prevBucket?.amount ?? 0
                return (
                  <div key={bucket.period_label} className="monthly-bar-row">
                    <span className="monthly-bar-row__label" style={{ fontSize: '11px', minWidth: '60px' }}>
                      {granularity === 'month' ? bucket.period_label.slice(5) : bucket.period_label.slice(5)}
                    </span>
                    <div className="monthly-bar-row__track">
                      <div
                        className="monthly-bar-row__fill"
                        style={{ width: `${(bucket.amount / maxAmount) * 100}%`, backgroundColor: '#3b82f6' }}
                      />
                    </div>
                    <div className="monthly-bar-row__track">
                      <div
                        className="monthly-bar-row__fill"
                        style={{ width: `${(prevAmount / maxAmount) * 100}%`, backgroundColor: '#9ca3af' }}
                      />
                    </div>
                    <span className="monthly-bar-row__count" style={{ fontSize: '11px', minWidth: '70px' }}>
                      {formatTND(bucket.amount)} / {formatTND(prevAmount)}
                    </span>
                  </div>
                )
              })}
              {data.period_n.buckets.length === 0 && <p>Aucune donnée pour cette période.</p>}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
