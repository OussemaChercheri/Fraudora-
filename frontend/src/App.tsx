import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import DashboardPage from './pages/DashboardPage'
import ForbiddenPage from './pages/ForbiddenPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import LoginPage from './pages/LoginPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import ThresholdsSettingsPage from './pages/admin/ThresholdsSettingsPage'
import UsersPage from './pages/admin/UsersPage'
import AnomaliesPage from './pages/anomalies/AnomaliesPage'
import SupplierRiskPage from './pages/anomalies/SupplierRiskPage'
import AnalysisDashboardPage from './pages/analysis/AnalysisDashboardPage'
import InvoiceDetailPage from './pages/invoices/InvoiceDetailPage'
import InvoicesListPage from './pages/invoices/InvoicesListPage'
import UploadPage from './pages/invoices/UploadPage'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/forbidden" element={<ForbiddenPage />} />
        <Route element={<Layout />}>
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/users"
            element={
              <ProtectedRoute requiredRole="ADMIN">
                <UsersPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/thresholds"
            element={
              <ProtectedRoute requiredRole="ADMIN">
                <ThresholdsSettingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/invoices"
            element={
              <ProtectedRoute>
                <InvoicesListPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/invoices/upload"
            element={
              <ProtectedRoute>
                <UploadPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/invoices/:id"
            element={
              <ProtectedRoute>
                <InvoiceDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analysis"
            element={
              <ProtectedRoute allowedRoles={['FINANCE', 'ADMIN', 'COMPTABLE']}>
                <AnalysisDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/anomalies"
            element={
              <ProtectedRoute allowedRoles={['COMPTABLE', 'FINANCE', 'ADMIN']}>
                <AnomaliesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/anomalies/suppliers"
            element={
              <ProtectedRoute allowedRoles={['FINANCE', 'ADMIN']}>
                <SupplierRiskPage />
              </ProtectedRoute>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
