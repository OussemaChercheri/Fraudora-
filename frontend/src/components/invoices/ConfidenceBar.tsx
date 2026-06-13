interface ConfidenceBarProps {
  confidence: number
  label?: string
  needsReview?: boolean
}

function getBarColor(percent: number): string {
  if (percent > 80) return 'var(--confidence-high, #16a34a)'
  if (percent >= 50) return 'var(--confidence-mid, #ea580c)'
  return 'var(--confidence-low, #dc2626)'
}

export default function ConfidenceBar({
  confidence,
  label,
  needsReview,
}: ConfidenceBarProps) {
  const percent = Math.round(confidence * 100)

  return (
    <div className="confidence-bar">
      <div className="confidence-bar__header">
        {label && <span className="confidence-bar__label">{label}</span>}
        <span className="confidence-bar__percent">{percent}%</span>
        {needsReview && (
          <span className="confidence-bar__warning" title="Needs review">
            ⚠ Needs review
          </span>
        )}
      </div>
      <div className="confidence-bar__track">
        <div
          className="confidence-bar__fill"
          style={{ width: `${percent}%`, backgroundColor: getBarColor(percent) }}
        />
      </div>
    </div>
  )
}
