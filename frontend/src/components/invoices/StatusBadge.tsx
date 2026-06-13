import type { InvoiceStatus } from '../../types/invoice'

const STATUS_LABELS: Record<InvoiceStatus, string> = {
  UPLOADED: 'Uploaded',
  PROCESSING: 'Processing',
  PROCESSED: 'Processed',
  REVIEW_REQUIRED: 'Review required',
  ERROR: 'Error',
}

export default function StatusBadge({ status }: { status: InvoiceStatus }) {
  const className = `invoice-status invoice-status--${status.toLowerCase()}`
  const isProcessing = status === 'PROCESSING'

  return (
    <span className={`${className}${isProcessing ? ' invoice-status--pulse' : ''}`}>
      {STATUS_LABELS[status]}
    </span>
  )
}
