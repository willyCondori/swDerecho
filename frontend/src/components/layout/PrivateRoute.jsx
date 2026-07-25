// components/layout/PrivateRoute.jsx
import { Navigate, Outlet } from 'react-router-dom'
import useAuthStore from '../../modules/auth/store/authStore'

export default function PrivateRoute({ adminOnly = false }) {
  const { isAuthenticated, isAdmin } = useAuthStore()

  if (!isAuthenticated()) return <Navigate to="/login" replace />
  if (adminOnly && !isAdmin()) return <Navigate to="/dashboard" replace />

  return <Outlet />
}
