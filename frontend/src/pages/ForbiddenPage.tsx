import { Link } from 'react-router-dom'

export default function ForbiddenPage() {
  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>403 — Forbidden</h1>
        <p>You do not have permission to access this page.</p>
        <Link to="/dashboard" className="link">
          Back to dashboard
        </Link>
      </div>
    </div>
  )
}
