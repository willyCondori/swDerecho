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
const CargaArticulosPage = lazy(() => import('../modules/catalogo/pages/articulos/CargaArticulosPage'))
const VerArticulos       = lazy(() => import('../modules/catalogo/pages/articulos/VerArticulos'))
const CrearUsuarios        = lazy(() => import('../modules/usuarios/pages/CrearUsuarioPage'))
const VerUsuarios        = lazy(() => import('../modules/usuarios/pages/UsuariosPage'))
const PerfilUsuarios       = lazy(() => import('../modules/usuarios/pages/PerfilUsuarioPage'))
const EditarUsuarios       = lazy(() => import('../modules/usuarios/pages/EditarUsuarioPage'))
const ClientesPage = lazy(() => import('../modules/clientes/pages/ClientesPage'))
const CrearClientePage  = lazy(() => import('../modules/clientes/pages/CrearClientePage'))



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
          <Route path="/catalogo/*"      element={<PageLoader />} />
          <Route path="/documentos/*"    element={<PageLoader />} />
          <Route path="/plantillas/*"    element={<PageLoader />} />
          <Route path="/ia/*"            element={<PageLoader />} />
          <Route path="/configuracion/*" element={<PageLoader />} />
        </Route>

        {/* Admin only */}
        <Route element={<PrivateRoute adminOnly />}>
          <Route element={<AppLayout />}>
            <Route path="/catalogo/articulos" element={
                <Suspense fallback={<PageLoader />}><VerArticulos /></Suspense>
              } />
            <Route path="/catalogo/cargar" element={
                <Suspense fallback={<PageLoader />}><CargaArticulosPage /></Suspense>
              } />
            <Route path="/auditoria/*" element={<PageLoader />} />

            {/* Usuarios — rutas explícitas en vez del wildcard */}
            <Route path="/usuarios" element={
                <Suspense fallback={<PageLoader />}><VerUsuarios /></Suspense>
              } />
            <Route path="/usuarios/nuevo" element={
                <Suspense fallback={<PageLoader />}><CrearUsuarios /></Suspense>
              } />
            <Route path="/usuarios/:id" element={
                <Suspense fallback={<PageLoader />}><PerfilUsuarios /></Suspense>
              } />
            <Route path="/usuarios/:id/editar" element={
                <Suspense fallback={<PageLoader />}><EditarUsuarios /></Suspense>
              } />
            <Route path="/clientes" element={
                <Suspense fallback={<PageLoader />}><ClientesPage /></Suspense>
              } />
            <Route path="/clientes/nuevo" element={
                <Suspense fallback={<PageLoader />}><CrearClientePage /></Suspense>
              } />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
