import { Navigate } from 'react-router-dom'

import { useAuthStore } from '../store/authStore'
import type { UserRole } from '../types/user'

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRole?: UserRole
  allowedRoles?: UserRole[]
}

export default function ProtectedRoute({
  children,
  requiredRole,
  allowedRoles,
}: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate to="/forbidden" replace />
  }

  if (requiredRole && user?.role !== requiredRole) {
    return <Navigate to="/forbidden" replace />
  }

  return children
}
