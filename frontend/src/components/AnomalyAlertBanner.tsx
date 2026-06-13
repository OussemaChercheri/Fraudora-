import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getAnomalyAlerts, reviewAnomalyAlert } from '../api/anomalies'
import { useAuthStore } from '../store/authStore'

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

function alertTypeLabel(type: string): string {
  if (type === 'ABNORMAL_AMOUNT') return 'Montant anormal'
  if (type === 'NEW_HIGH_RISK_SUPPLIER') return 'Nouveau fournisseur'
  if (type === 'PRICE_SPIKE') return 'Pic de prix'
  return type
}

function formatMetric(metricValue: number, thresholdValue: number): string {
  return `${metricValue.toFixed(2)} (seuil: ${thresholdValue.toFixed(2)})`
}

interface AnomalyAlertBannerProps {
  invoiceId: string
}

export default function AnomalyAlertBanner({ invoiceId }: AnomalyAlertBannerProps) {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const canReview = user && ['COMPTABLE', 'FINANCE', 'ADMIN'].includes(user.role)

  const { data: alerts, isLoading } = useQuery({
    queryKey: ['anomaly-alerts', invoiceId],
    queryFn: () => getAnomalyAlerts(invoiceId),
    enabled: !!invoiceId,
  })

  const reviewMutation = useMutation({
    mutationFn: ({ alertId, status }: { alertId: string; status: 'ACKNOWLEDGED' | 'DISMISSED' }) =>
      reviewAnomalyAlert(alertId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['anomaly-alerts', invoiceId] })
      queryClient.invalidateQueries({ queryKey: ['pending-anomalies'] })
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    },
  })

  if (isLoading) return null
  if (!alerts || alerts.length === 0) return null

  const pendingAlerts = alerts.filter((a) => a.status === 'PENDING')
  const reviewedAlerts = alerts.filter((a) => a.status !== 'PENDING')
  if (pendingAlerts.length === 0 && reviewedAlerts.length === 0) return null

  return (
    <div className="anomaly-banner">
      <div className="anomaly-banner__header">
        <span>Alertes anomalies détectées</span>
        <span className="anomaly-banner__count">{alerts.length}</span>
      </div>
      <div className="anomaly-banner__list">
        {alerts.map((alert) => {
          const isPending = alert.status === 'PENDING'
          const isDismissed = alert.status === 'DISMISSED'
          const isAcknowledged = alert.status === 'ACKNOWLEDGED'
          return (
            <div
              key={alert.id}
              className={`anomaly-banner__item ${severityClass(alert.severity)} ${!isPending ? 'anomaly-banner__item--resolved' : ''}`}
            >
              <div className="anomaly-banner__item-header">
                <span className="anomaly-banner__type">
                  {alertTypeIcon(alert.alert_type)} {alertTypeLabel(alert.alert_type)}
                </span>
                <span className={`severity-badge ${severityClass(alert.severity)}`}>
                  {alert.severity}
                </span>
                {isDismissed && <span className="status-badge status-badge--dismissed">Ignoré</span>}
                {isAcknowledged && <span className="status-badge status-badge--acknowledged">Accepté</span>}
              </div>
              <p className="anomaly-banner__desc">{alert.description}</p>
              <p className="anomaly-banner__metric">
                Valeur: {formatMetric(alert.metric_value, alert.threshold_value)}
              </p>
              {isPending && canReview && (
                <div className="anomaly-banner__actions">
                  <button
                    type="button"
                    className="btn btn-sm btn-primary"
                    disabled={reviewMutation.isPending}
                    onClick={() =>
                      reviewMutation.mutate({ alertId: alert.id, status: 'ACKNOWLEDGED' })
                    }
                  >
                    Accepter
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm btn-secondary"
                    disabled={reviewMutation.isPending}
                    onClick={() =>
                      reviewMutation.mutate({ alertId: alert.id, status: 'DISMISSED' })
                    }
                  >
                    Ignorer
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
