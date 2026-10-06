// components/layout/AppLayout.jsx
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import useAuthStore from '../../modules/auth/store/authStore'
import NotificacionesBell from './NotificacionesBell'
import styles from './AppLayout.module.css'

const NAV_ITEMS = [
  {
    section: 'General',
    items: [
      { to: '/dashboard', icon: 'ti-layout-dashboard', label: 'Dashboard' },
      { to: '/casos',     icon: 'ti-folder',           label: 'Casos',     badge: null },
      { to: '/clientes',  icon: 'ti-users',            label: 'Clientes' },
    ],
  },
  {
    section: 'Catálogo jurídico',
    items: [
      { to: '/catalogo/articulos', icon: 'ti-book', label: 'Artículos' },
      { to: '/catalogo/normas', icon: 'ti-books', label: 'Normas', adminOnly: true },
      { to: '/catalogo/administrar', icon: 'ti-adjustments', label: 'Ramas y jerarquías', adminOnly: true },
    ],
  },
  {
    section: 'Fuentes y documentos',
    items: [
      { to: '/catalogo/gaceta', icon: 'ti-building-bank', label: 'Gaceta Oficial' },
      { to: '/catalogo/cargar', icon: 'ti-file-upload', label: 'Cargar documentos' },
    ],
  },
  {
    section: 'Vigencia normativa',
    items: [
      { to: '/catalogo/avisos', icon: 'ti-bell', label: 'Avisos normativos' },
      { to: '/catalogo/historial', icon: 'ti-history', label: 'Historial de cambios', adminOnly: true },
      { to: '/catalogo/restaurar', icon: 'ti-restore', label: 'Restaurar cambios', adminOnly: true },
    ],
  },
  {
    section: 'Sistema',
    items: [
      { to: '/auditoria',    icon: 'ti-shield-check', label: 'Auditoría',    adminOnly: true },
      { to: '/usuarios',     icon: 'ti-users-group',  label: 'Usuarios',     adminOnly: true },
      { to: '/usuarios/roles', icon: 'ti-shield-lock', label: 'Roles',       adminOnly: true },
//      { to: '/configuracion',icon: 'ti-settings',     label: 'Configuración' },
    ],
  },
]

function getInitials(user) {
  if (!user) return '?'
  const p = user.perfil
  if (p?.nombres && p?.apellidos)
    return `${p.nombres[0]}${p.apellidos[0]}`.toUpperCase()
  return user.usuario?.slice(0, 2).toUpperCase() || '?'
}

export default function AppLayout() {
  const navigate   = useNavigate()
  const { user, logout, isAdmin } = useAuthStore()
  const admin = isAdmin()
  const { pathname } = useLocation()
  const seccionActual = NAV_ITEMS.find((s) => s.items.some((item) =>
    (!item.adminOnly || admin) && (pathname === item.to || pathname.startsWith(item.to + '/'))))?.section
  const [seccionesAbiertas, setSeccionesAbiertas] = useState(() => Object.fromEntries(NAV_ITEMS.map((s) => [s.section, true])))

  useEffect(() => {
    if (seccionActual) setSeccionesAbiertas((actual) => ({ ...actual, [seccionActual]: true }))
  }, [seccionActual])

  // En pantallas chicas el menú lateral es un panel que se abre con el botón
  // de la barra superior.
  const [menuAbierto, setMenuAbierto] = useState(false)

  // Al cambiar de página se cierra el menú.
  useEffect(() => {
    setMenuAbierto(false)
  }, [pathname])

  // Con el menú abierto: Escape lo cierra y el fondo no se desplaza.
  useEffect(() => {
    if (!menuAbierto) return undefined
    const alTeclear = (e) => { if (e.key === 'Escape') setMenuAbierto(false) }
    document.addEventListener('keydown', alTeclear)
    const overflowPrevio = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', alTeclear)
      document.body.style.overflow = overflowPrevio
    }
  }, [menuAbierto])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className={styles.root}>
      {/* ── Sidebar ─────────────────────────────────────── */}
      {menuAbierto && (
        <div
          className={styles.overlay}
          onClick={() => setMenuAbierto(false)}
          aria-hidden="true"
        />
      )}

      <aside
        id="sidebar-principal"
        className={`${styles.sidebar} ${menuAbierto ? styles.sidebarOpen : ''}`}
        aria-label="Navegación principal"
      >
        <div className={styles.sidebarLogo}>
          <div className={styles.sidebarLogoIcon}>⚖</div>
          <span className={styles.sidebarLogoText}>Litigiun</span>
          <button
            type="button"
            className={styles.sidebarCloseBtn}
            onClick={() => setMenuAbierto(false)}
            aria-label="Cerrar menú"
          >
            <i className="ti ti-x" aria-hidden="true" />
          </button>
        </div>

        <nav className={styles.sidebarNav}>
          {NAV_ITEMS.map((section, indice) => {
            const visible = section.items.filter(
              (item) => !item.adminOnly || admin,
            )
            if (!visible.length) return null
            const abierta = Boolean(seccionesAbiertas[section.section])
            const submodulosId = `sidebar-submodulos-${indice}`
            return (
              <div key={section.section} className={styles.navSection}>
                <button type="button" className={styles.navSectionToggle}
                  aria-expanded={abierta} aria-controls={submodulosId}
                  onClick={() => setSeccionesAbiertas((actual) => ({ ...actual, [section.section]: !actual[section.section] }))}>
                  <span>{section.section}</span>
                  <i className={`ti ti-chevron-right ${abierta ? styles.sectionExpanded : ''}`} aria-hidden="true" />
                </button>
                <div id={submodulosId} hidden={!abierta}>
                {visible.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/usuarios'}
                    className={({ isActive }) =>
                      `${styles.navItem} ${isActive ? styles.active : ''}`
                    }
                  >
                    <span className={styles.navIcon}>
                      <i className={`ti ${item.icon}`} aria-hidden="true" />
                    </span>
                    {item.label}
                    {item.badge != null && (
                      <span className={styles.navBadge}>{item.badge}</span>
                    )}
                    {item.dot && (
                      <span className={`${styles.navBadge} ${styles.online}`}>
                        <span className={styles.navBadgeDot} />
                      </span>
                    )}
                  </NavLink>
                ))}
                </div>
              </div>
            )
          })}
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.userCard}>
            <div className={styles.userAvatar}>{getInitials(user)}</div>
            <div className={styles.userInfo}>
              <p className={styles.userName}>{user?.usuario || '—'}</p>
              <p className={styles.userRole}>{typeof user?.rol === 'string' ? user.rol : user?.rol?.nombre || 'Sin rol'}</p>
            </div>
            <button
              className={styles.logoutBtn}
              onClick={handleLogout}
              aria-label="Cerrar sesión"
            >
              <i className="ti ti-logout" aria-hidden="true" />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Topbar ──────────────────────────────────────── */}
      <header className={styles.topbar}>
        <div className={styles.topbarLeft}>
          <button
            type="button"
            className={`${styles.topbarBtn} ${styles.menuBtn}`}
            onClick={() => setMenuAbierto(true)}
            aria-label="Abrir menú"
            aria-expanded={menuAbierto}
            aria-controls="sidebar-principal"
          >
            <i className="ti ti-menu-2" aria-hidden="true" />
          </button>
          <nav className={styles.breadcrumb} aria-label="Ruta de navegación">
            <span>Litiguin</span>
            <span className={styles.breadcrumbSep}>/</span>
            <span className={styles.breadcrumbCurrent} id="page-title">Panel</span>
          </nav>
        </div>
        <div className={styles.topbarRight}>
          <NotificacionesBell />
          <button className={styles.topbarBtn} aria-label="Ayuda">
            <i className="ti ti-help-circle" aria-hidden="true" />
          </button>
        </div>
      </header>

      {/* ── Contenido principal ─────────────────────────── */}
      <main className={styles.main} id="main-content">
        <Outlet />
      </main>
    </div>
  )
}
