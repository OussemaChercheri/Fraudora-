import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { getPendingAnomalies, reviewAnomalyAlert } from '../../api/anomalies'
import { useAuthStore } from '../../store/authStore'
import type { AlertType, Severity } from '../../types/anomaly'

const ALERT_TYPE_OPTIONS: Array<{ value: '' | AlertType; label: string }> = [
  { value: '', label: 'Tous les types' },
  { value: 'ABNORMAL_AMOUNT', label: 'Montant anormal' },
  { value: 'NEW_HIGH_RISK_SUPPLIER', label: 'Nouveau fournisseur' },
  { value: 'PRICE_SPIKE', label: 'Pic de prix' },
]

const SEVERITY_OPTIONS: Array<{ value: '' | Severity; label: string }> = [
  { value: '', label: 'Toutes sévérités' },
  { value: 'HIGH', label: 'Haute' },
  { value: 'MEDIUM', label: 'Moyenne' },
  { value: 'LOW', label: 'Basse' },
]

function severityClass(severity: string): string {
  if (severity === 'HIGH') return 'severity--high'
  if (severity === 'MEDIUM') return 'severity--medium'
  return 'severity--low'
}

function alertTypeIcon(type: string): string {
  if (type === 'ABNORMAL_AMOUNT') return '💰'
  if (type === 'NEW_HIGH_RISK_SUPPLIER') return '🆕'
  if (type === 'PRICE_SPIKE') return '📈'
  return '⚠️'
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function AnomaliesPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const canReview = user && ['COMPTABLE', 'FINANCE', 'ADMIN'].includes(user.role)

  const [page, setPage] = useState(1)
  const [typeFilter, setTypeFilter] = useState<'' | AlertType>('')
  const [severityFilter, setSeverityFilter] = useState<'' | Severity>('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['pending-anomalies', page, typeFilter, severityFilter],
    queryFn: () =>
      getPendingAnomalies({
        page,
        page_size: 20,
        alert_type: typeFilter || undefined,
        severity: severityFilter || undefined,
      }),
  })

  const reviewMutation = useMutation({
    mutationFn: ({ alertId, status }: { alertId: string; status: 'ACKNOWLEDGED' | 'DISMISSED' }) =>
      reviewAnomalyAlert(alertId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-anomalies'] })
    },
  })

  return (
    <div className="page-container page-container--wide">
      <div className="page-header">
        <h1>Alertes anomalies</h1>
      </div>

      <div className="filters-bar">
        <div className="form-field">
          <label htmlFor="alert_type">Type</label>
          <select
            id="alert_type"
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value as '' | AlertType)
              setPage(1)
            }}
          >
            {ALERT_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label htmlFor="severity">Sévérité</label>
          <select
            id="severity"
            value={severityFilter}
            onChange={(e) => {
              setSeverityFilter(e.target.value as '' | Severity)
              setPage(1)
            }}
          >
            {SEVERITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && <p>Chargement des alertes…</p>}
      {isError && <p className="form-error">Erreur lors du chargement des alertes.</p>}

      {!isLoading && !isError && (
        <>
          <div className="table-wrapper">
            <table className="data-table data-table--clickable">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Sévérité</th>
                  <th>Description</th>
                  <th>Statut</th>
                  <th>Facture</th>
                  <th>Date</th>
                  {canReview && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {data?.items.map((alert) => (
                  <tr
                    key={alert.id}
                    onClick={() => navigate(`/invoices/${alert.invoice_id}`)}
                  >
                    <td>
                      <span className="anomaly-type-cell">
                        {alertTypeIcon(alert.alert_type)}
                        <span>{alert.alert_type.replace(/_/g, ' ')}</span>
                      </span>
                    </td>
                    <td>
                      <span className={`severity-badge ${severityClass(alert.severity)}`}>
                        {alert.severity}
                      </span>
                    </td>
                    <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {alert.description}
                    </td>
                    <td>
                      <span className={`status-badge status-badge--${alert.status.toLowerCase()}`}>
                        {alert.status === 'PENDING' && 'En attente'}
                        {alert.status === 'ACKNOWLEDGED' && 'Accepté'}
                        {alert.status === 'DISMISSED' && 'Ignoré'}
                        {alert.status === 'PROCESSED' && 'Traité'}
                      </span>
                    </td>
                    <td>
                      <Link
                        to={`/invoices/${alert.invoice_id}`}
                        className="link link--inline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {alert.invoice.original_filename}
                      </Link>
                    </td>
                    <td>{formatDate(alert.created_at)}</td>
                    {canReview && (
                      <td>
                        {alert.status === 'PENDING' && (
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                              type="button"
                              className="btn btn-primary btn-sm"
                              disabled={reviewMutation.isPending}
                              onClick={(e) => {
                                e.stopPropagation()
                                reviewMutation.mutate({ alertId: alert.id, status: 'ACKNOWLEDGED' })
                              }}
                            >
                              Accepter
                            </button>
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              disabled={reviewMutation.isPending}
                              onClick={(e) => {
                                e.stopPropagation()
                                reviewMutation.mutate({ alertId: alert.id, status: 'DISMISSED' })
                              }}
                            >
                              Ignorer
                            </button>
                          </div>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
                {data?.items.length === 0 && (
                  <tr>
                    <td colSpan={canReview ? 7 : 6} style={{ textAlign: 'center' }}>
                      Aucune anomalie en attente.
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
                Précédent
              </button>
              <span className="pagination__info">
                Page {data.page} sur {Math.max(data.total_pages, 1)} ({data.total} total)
              </span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={page >= data.total_pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Suivant
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
