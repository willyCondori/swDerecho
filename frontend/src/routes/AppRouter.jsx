// routes/AppRouter.jsx
import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout   from '../components/layout/AppLayout'
import PrivateRoute from '../components/layout/PrivateRoute'
import LoginPage   from '../modules/auth/pages/LoginPage'
import DashboardPage from '../modules/dashboard/pages/DashboardPage'

// Páginas lazy (se crean en siguientes módulos)
import { lazy, Suspense } from 'react'

const CasosPage      = lazy(() => import('../modules/casos/pages/CasosPage'))
const NuevoCasoPage  = lazy(() => import('../modules/casos/pages/NuevoCasoPage'))
const CasoDetailPage = lazy(() => import('../modules/casos/pages/CasoDetailPage'))
const CargaArticulosPage = lazy(() => import('../modules/catalogo/pages/CargaArticulosPage'))

function PageLoader() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '60vh', color: 'var(--c-text-muted)', fontSize: 13,
      gap: 10,
    }}>
      <span style={{
        width: 18, height: 18, border: '2px solid var(--c-border-strong)',
        borderTopColor: 'var(--c-purple-500)', borderRadius: '50%',
        animation: 'spin 0.7s linear infinite',
        display: 'inline-block',
      }} />
      Cargando...
    </div>
  )
}

export default function AppRouter() {
  return (
    <Routes>
      {/* Pública */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protegidas */}
      <Route element={<PrivateRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />

          <Route path="/casos" element={
            <Suspense fallback={<PageLoader />}><CasosPage /></Suspense>
          } />
          <Route path="/casos/nuevo" element={
            <Suspense fallback={<PageLoader />}><NuevoCasoPage /></Suspense>
          } />
          <Route path="/casos/:id" element={
            <Suspense fallback={<PageLoader />}><CasoDetailPage /></Suspense>
          } />

          {/* Rutas pendientes de implementar */}
          <Route path="/clientes/*"      element={<PageLoader />} />
          <Route path="/catalogo/*"      element={<PageLoader />} />
          <Route path="/documentos/*"    element={<PageLoader />} />
          <Route path="/plantillas/*"    element={<PageLoader />} />
          <Route path="/ia/*"            element={<PageLoader />} />
          <Route path="/configuracion/*" element={<PageLoader />} />
        </Route>

        {/* Admin only */}
        <Route element={<PrivateRoute adminOnly />}>
          <Route element={<AppLayout />}>
            <Route path="/catalogo/cargar" element={
                <Suspense fallback={<PageLoader />}><CargaArticulosPage /></Suspense>
              } />
            <Route path="/auditoria/*" element={<PageLoader />} />
            <Route path="/usuarios/*"  element={<PageLoader />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
