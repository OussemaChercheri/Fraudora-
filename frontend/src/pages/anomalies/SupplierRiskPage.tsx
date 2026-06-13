import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { getSupplierRiskScores, recomputeRiskScores } from '../../api/anomalies'

function scoreClass(score: number): string {
  if (score >= 70) return 'severity--high'
  if (score >= 40) return 'severity--medium'
  return 'severity--low'
}

function formatDate(dateString: string | null) {
  if (!dateString) return '—'
  return new Date(dateString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export default function SupplierRiskPage() {
  const queryClient = useQueryClient()
  const [minScore, setMinScore] = useState('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['supplier-risk-scores', minScore],
    queryFn: () =>
      getSupplierRiskScores(minScore ? parseInt(minScore, 10) : undefined),
  })

  const recomputeMutation = useMutation({
    mutationFn: recomputeRiskScores,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supplier-risk-scores'] })
    },
  })

  return (
    <div className="page-container page-container--wide">
      <div className="page-header">
        <h1>Risques fournisseurs</h1>
        <button
          type="button"
          className="btn btn-primary"
          disabled={recomputeMutation.isPending}
          onClick={() => recomputeMutation.mutate()}
        >
          {recomputeMutation.isPending ? (
            <span className="btn-with-spinner">
              <span className="spinner spinner--sm" />
              Recalcul…
            </span>
          ) : (
            'Recalculer les scores'
          )}
        </button>
      </div>

      <div className="filters-bar">
        <div className="form-field">
          <label htmlFor="min_score">Score minimum</label>
          <input
            id="min_score"
            type="number"
            min="0"
            max="100"
            placeholder="0"
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
          />
        </div>
      </div>

      {recomputeMutation.data && (
        <div className="form-success">{recomputeMutation.data.message}</div>
      )}
      {recomputeMutation.isError && (
        <p className="form-error">Erreur lors du recalcul des scores.</p>
      )}

      {isLoading && <p>Chargement des scores…</p>}
      {isError && <p className="form-error">Erreur lors du chargement.</p>}

      {!isLoading && !isError && (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Fournisseur</th>
                <th>Score risque</th>
                <th>Factures</th>
                <th>Montant total</th>
                <th>Moyenne</th>
                <th>Anomalies</th>
                <th>Dernière facture</th>
              </tr>
            </thead>
            <tbody>
              {(data ?? [])
                .sort((a, b) => b.risk_score - a.risk_score)
                .map((supplier) => (
                  <tr key={supplier.id}>
                    <td style={{ fontWeight: 500 }}>{supplier.supplier_name}</td>
                    <td>
                      <span className={`severity-badge ${scoreClass(supplier.risk_score)}`}>
                        {supplier.risk_score}/100
                      </span>
                    </td>
                    <td>{supplier.total_invoices}</td>
                    <td>{supplier.total_amount_sum.toFixed(2)}</td>
                    <td>{supplier.avg_amount.toFixed(2)}</td>
                    <td>{supplier.anomaly_count}</td>
                    <td>{formatDate(supplier.last_invoice_date)}</td>
                  </tr>
                ))}
              {(!data || data.length === 0) && (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center' }}>
                    Aucun score fournisseur disponible.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
