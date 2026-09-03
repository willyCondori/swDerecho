// components/layout/PrivateRoute.jsx
import { Navigate, Outlet } from 'react-router-dom'
import useAuthStore from '../../modules/auth/store/authStore'

function BootstrapLoader() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100vh', color: 'var(--c-text-muted)', fontSize: 13,
      gap: 10,
    }}>
      <span style={{
        width: 18, height: 18, border: '2px solid var(--c-border-strong)',
        borderTopColor: 'var(--c-purple-500)', borderRadius: '50%',
        animation: 'spin 0.7s linear infinite',
        display: 'inline-block',
      }} />
      Cargando sesión...
    </div>
  )
}

export default function PrivateRoute({ adminOnly = false, requiereEscritura = false }) {
  const { isAuthenticated, isAdmin, puedeEscribir, isBootstrapping } = useAuthStore()

  // El access token vive solo en memoria: recién montada la app todavía
  // no sabemos si hay una sesión válida hasta que bootstrap() (en
  // App.jsx) termine de intentar restaurarla con la cookie httpOnly.
  // Redirigir a /login antes de eso mandaría afuera a alguien con una
  // sesión perfectamente válida, solo por haber recargado la página.
  if (isBootstrapping) return <BootstrapLoader />

  if (!isAuthenticated()) return <Navigate to="/login" replace />
  if (adminOnly && !isAdmin()) return <Navigate to="/dashboard" replace />

  // Rutas de creación/edición: Asistente es de solo lectura (espeja el
  // permiso EsOperativo del backend). 
  if (requiereEscritura && !puedeEscribir()) return <Navigate to="/dashboard" replace />

  return <Outlet />
}