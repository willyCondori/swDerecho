// components/layout/AppLayout.jsx
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import useAuthStore from '../../modules/auth/store/authStore'
import styles from './AppLayout.module.css'

const NAV_ITEMS = [
  {
    section: 'General',
    items: [
      { to: '/dashboard', icon: 'ti-layout-dashboard', label: 'Dashboard' },
      { to: '/casos',     icon: 'ti-folder',           label: 'Casos',     badge: null },
      { to: '/clientes',  icon: 'ti-users',            label: 'Clientes' },
      { to: '/ia',        icon: 'ti-cpu',              label: 'Análisis IA', dot: true },
    ],
  },
  {
    section: 'Catálogo',
    items: [
      { to: '/catalogo',    icon: 'ti-book',      label: 'Artículos' },
      { to: '/documentos',  icon: 'ti-file-text', label: 'Documentos' },
      { to: '/plantillas',  icon: 'ti-template',  label: 'Plantillas' },
    ],
  },
  {
    section: 'Sistema',
    items: [
      { to: '/auditoria',    icon: 'ti-shield-check', label: 'Auditoría',    adminOnly: true },
      { to: '/usuarios',     icon: 'ti-users-group',  label: 'Usuarios',     adminOnly: true },
      { to: '/configuracion',icon: 'ti-settings',     label: 'Configuración' },
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

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className={styles.root}>
      {/* ── Sidebar ─────────────────────────────────────── */}
      <aside className={styles.sidebar} aria-label="Navegación principal">
        <div className={styles.sidebarLogo}>
          <div className={styles.sidebarLogoIcon}>⚖</div>
          <span className={styles.sidebarLogoText}>JurisIA</span>
        </div>

        <nav className={styles.sidebarNav}>
          {NAV_ITEMS.map((section) => {
            const visible = section.items.filter(
              (item) => !item.adminOnly || admin,
            )
            if (!visible.length) return null
            return (
              <div key={section.section} className={styles.navSection}>
                <p className={styles.navSectionLabel}>{section.section}</p>
                {visible.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
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
            )
          })}
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.userCard}>
            <div className={styles.userAvatar}>{getInitials(user)}</div>
            <div className={styles.userInfo}>
              <p className={styles.userName}>{user?.usuario || '—'}</p>
              <p className={styles.userRole}>{user?.rol?.nombre || 'Sin rol'}</p>
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
          <nav className={styles.breadcrumb} aria-label="Ruta de navegación">
            <span>JurisIA</span>
            <span className={styles.breadcrumbSep}>/</span>
            <span className={styles.breadcrumbCurrent} id="page-title">Panel</span>
          </nav>
        </div>
        <div className={styles.topbarRight}>
          <button className={`${styles.topbarBtn} ${styles.topbarBtnBadge}`} aria-label="Notificaciones">
            <i className="ti ti-bell" aria-hidden="true" />
          </button>
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
