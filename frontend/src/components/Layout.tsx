import { useQuery } from '@tanstack/react-query'
import { NavLink, Outlet } from 'react-router-dom'

import { getPendingAnomalies } from '../api/anomalies'
import NotificationBell from './NotificationBell'
import { useAuthStore } from '../store/authStore'
import { APP_NAME } from '../utils/constants'

export default function Layout() {
  const user = useAuthStore((state) => state.user)
  const canViewAnomalies = user && ['COMPTABLE', 'FINANCE', 'ADMIN'].includes(user.role)
  const canViewRiskScores = user && ['FINANCE', 'ADMIN'].includes(user.role)

  const { data: pendingData } = useQuery({
    queryKey: ['pending-anomalies-count'],
    queryFn: () => getPendingAnomalies({ page_size: 1 }),
    refetchInterval: 30000,
    enabled: !!canViewAnomalies,
  })

  const pendingCount = pendingData?.total ?? 0

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar__header">
          <h1>{APP_NAME}</h1>
        </div>
        <nav className="sidebar__nav">
          <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'sidebar__link sidebar__link--active' : 'sidebar__link'}>
            Dashboard
          </NavLink>
          <NavLink to="/invoices" end className={({ isActive }) => isActive ? 'sidebar__link sidebar__link--active' : 'sidebar__link'}>
            Factures
          </NavLink>
          <NavLink to="/anomalies" className={({ isActive }) => isActive ? 'sidebar__link sidebar__link--active' : 'sidebar__link'}>
            Anomalies
            {pendingCount > 0 && <span className="sidebar__badge">{pendingCount}</span>}
          </NavLink>
          {canViewRiskScores && (
            <NavLink to="/anomalies/suppliers" className={({ isActive }) => isActive ? 'sidebar__link sidebar__link--active' : 'sidebar__link'}>
              Risques fournisseurs
            </NavLink>
          )}
          <NavLink to="/analysis" className={({ isActive }) => isActive ? 'sidebar__link sidebar__link--active' : 'sidebar__link'}>
            Analyse OCR
          </NavLink>
          {user?.role === 'ADMIN' && (
            <>
              <NavLink to="/admin/users" className={({ isActive }) => isActive ? 'sidebar__link sidebar__link--active' : 'sidebar__link'}>
                Utilisateurs
              </NavLink>
              <NavLink to="/admin/thresholds" className={({ isActive }) => isActive ? 'sidebar__link sidebar__link--active' : 'sidebar__link'}>
                Paramètres &gt; Seuils d'alerte
              </NavLink>
            </>
          )}
        </nav>
        <div className="sidebar__footer">
          {user && (
            <span className="sidebar__user">
              {user.full_name}
              <span className="sidebar__user-role">{user.role}</span>
            </span>
          )}
        </div>
      </aside>
      <div className="app-content">
        <header className="topbar">
          <NotificationBell />
          {user && <span className="topbar__user">{user.full_name}</span>}
        </header>
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
