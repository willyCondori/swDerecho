// routes/AppRouter.jsx
import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout   from '../components/layout/AppLayout'
import PrivateRoute from '../components/layout/PrivateRoute'
import LoginPage   from '../modules/auth/pages/LoginPage'
import CambiarPasswordObligatorioPage from '../modules/auth/pages/CambiarPasswordObligatorioPage'
import DashboardPage from '../modules/dashboard/pages/DashboardPage'
import useAuthStore from '../modules/auth/store/authStore'

// Páginas lazy (se crean en siguientes módulos)
import { lazy, Suspense } from 'react'

const CasosPage      = lazy(() => import('../modules/casos/pages/CasosPage'))
const NuevoCasoPage  = lazy(() => import('../modules/casos/pages/NuevoCasoPage'))
const CasoDetailPage = lazy(() => import('../modules/casos/pages/CasoDetailPage'))
const EditarCasoPage = lazy(() => import('../modules/casos/pages/EditarCasoPage'))
const CargaArticulosPage = lazy(() => import('../modules/catalogo/pages/articulos/CargaArticulosPage'))
const VerArticulos       = lazy(() => import('../modules/catalogo/pages/articulos/VerArticulos'))
const CrearUsuarios        = lazy(() => import('../modules/usuarios/pages/CrearUsuarioPage'))
const VerUsuarios        = lazy(() => import('../modules/usuarios/pages/UsuariosPage'))
const PerfilUsuarios       = lazy(() => import('../modules/usuarios/pages/PerfilUsuarioPage'))
const EditarUsuarios       = lazy(() => import('../modules/usuarios/pages/EditarUsuarioPage'))
const RolesPage           = lazy(() => import('../modules/usuarios/pages/RolesPage'))
const ClientesPage = lazy(() => import('../modules/clientes/pages/ClientesPage'))
const CrearClientePage  = lazy(() => import('../modules/clientes/pages/CrearClientePage'))
const ClienteCasosPage = lazy(() => import('../modules/clientes/pages/ClienteCasosPage'))
const AuditoriaPage    = lazy(() => import('../modules/auditoria/pages/AuditoriaPage'))


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

function RutaCambioPassword() {
  const { isAuthenticated, isBootstrapping } = useAuthStore()
  if (isBootstrapping) return null
  if (!isAuthenticated()) return <Navigate to="/login" replace />
  return <CambiarPasswordObligatorioPage />
}

export default function AppRouter() {
  return (
    <Routes>
      {/* Pública */}
      <Route path="/login" element={<LoginPage />} />

      {/* Cambio de contraseña obligatorio del primer login: requiere
          sesión pero NO pasa por PrivateRoute, porque PrivateRoute
          redirige acá mismo mientras el flag siga activo (evita el
          loop de redirecciones). */}
      <Route path="/cambiar-password" element={<RutaCambioPassword />} />

      {/* Protegidas */}
      <Route element={<PrivateRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />

          {/* Casos — lectura: cualquier autenticado (Asistente incluido,
              ve solo los suyos gracias al filtro del backend) */}
          <Route path="/casos" element={
            <Suspense fallback={<PageLoader />}><CasosPage /></Suspense>
          } />
          <Route path="/casos/:id" element={
            <Suspense fallback={<PageLoader />}><CasoDetailPage /></Suspense>
          } />

          {/* Clientes — lectura: cualquier autenticado */}
          <Route path="/clientes" element={
            <Suspense fallback={<PageLoader />}><ClientesPage /></Suspense>
          } />
          <Route path="/clientes/:id" element={
            <Suspense fallback={<PageLoader />}><ClienteCasosPage /></Suspense>
          } />

          {/* Catálogo — lectura: cualquier autenticado (espeja
              EsUsuarioAutenticado en ArticuloViewSet.get_permissions,
              que permite list/retrieve/por_norma/por_rama/entidades
              a Admin, Abogado y Asistente por igual) */}
          <Route path="/catalogo/articulos" element={
            <Suspense fallback={<PageLoader />}><VerArticulos /></Suspense>
          } />

          {/* Rutas pendientes de implementar */}
          <Route path="/documentos/*"    element={<PageLoader />} />
          <Route path="/plantillas/*"    element={<PageLoader />} />
          <Route path="/ia/*"            element={<PageLoader />} />
          <Route path="/configuracion/*" element={<PageLoader />} />
        </Route>

        {/* Requiere permisos de escritura (admin o abogado) — Asistente
            queda afuera, espejando el permiso EsOperativo del backend */}
        <Route element={<PrivateRoute requiereEscritura />}>
          <Route element={<AppLayout />}>
            <Route path="/casos/nuevo" element={
              <Suspense fallback={<PageLoader />}><NuevoCasoPage /></Suspense>
            } />
            <Route path="/casos/:id/editar" element={
              <Suspense fallback={<PageLoader />}><EditarCasoPage /></Suspense>
            } />
            <Route path="/clientes/nuevo" element={
              <Suspense fallback={<PageLoader />}><CrearClientePage /></Suspense>
            } />

            {/* Carga de PDFs de normas — espeja EsOperativo en
                carga_articulos_view.py: Admin y Abogado pueden cargar
                y sobrescribir el catálogo, Asistente no. */}
            <Route path="/catalogo/cargar" element={
              <Suspense fallback={<PageLoader />}><CargaArticulosPage /></Suspense>
            } />
          </Route>
        </Route>

        {/* Admin only */}
        <Route element={<PrivateRoute adminOnly />}>
          <Route element={<AppLayout />}>
            <Route path="/auditoria" element={
                <Suspense fallback={<PageLoader />}><AuditoriaPage /></Suspense>
              } />

            {/* Usuarios — rutas explícitas en vez del wildcard */}
            <Route path="/usuarios" element={
                <Suspense fallback={<PageLoader />}><VerUsuarios /></Suspense>
              } />
            <Route path="/usuarios/nuevo" element={
                <Suspense fallback={<PageLoader />}><CrearUsuarios /></Suspense>
              } />
            <Route path="/usuarios/roles" element={
                <Suspense fallback={<PageLoader />}><RolesPage /></Suspense>
              } />
            <Route path="/usuarios/:id" element={
                <Suspense fallback={<PageLoader />}><PerfilUsuarios /></Suspense>
              } />
            <Route path="/usuarios/:id/editar" element={
                <Suspense fallback={<PageLoader />}><EditarUsuarios /></Suspense>
              } />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}