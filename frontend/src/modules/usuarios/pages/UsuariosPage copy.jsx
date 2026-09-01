// modules/usuarios/pages/UsuariosPage.jsx
import { useNavigate } from 'react-router-dom'
import useUsuarios from '../hooks/useUsuarios'
import UsuarioTable from '../components/UsuarioTable'
import styles from './UsuariosPage.module.css'

const TABS = [
  { value: 'activos', label: 'Activos' },
  { value: 'eliminados', label: 'Eliminados' },
]

export default function UsuariosPage() {
  const navigate = useNavigate()
  const {
    usuarios,
    loading,
    error,
    search,
    setSearch,
    page,
    setPage,
    totalPages,
    count,
    estadoFiltro,
    setEstadoFiltro,
    reload,
    eliminarUsuario,
    recuperarUsuario,
  } = useUsuarios()

  const handleEliminar = async (usuario) => {
    const nombre = usuario.perfil?.nombres || usuario.usuario || 'este usuario'
    if (!window.confirm(`¿Eliminar a ${nombre}? Podrás recuperarlo luego desde la pestaña "Eliminados".`)) return
    try {
      await eliminarUsuario(usuario.id)
    } catch (e) {
      window.alert(e?.response?.data?.detail || 'No se pudo eliminar el usuario.')
    }
  }

  const handleRecuperar = async (usuario) => {
    const nombre = usuario.perfil?.nombres || usuario.usuario || 'este usuario'
    if (!window.confirm(`¿Recuperar a ${nombre}? Volverá a poder iniciar sesión.`)) return
    try {
      await recuperarUsuario(usuario.id)
    } catch (e) {
      window.alert(e?.response?.data?.detail || 'No se pudo recuperar el usuario.')
    }
  }

  return (
    <div className={styles.root}>
      {/* ── Encabezado ─────────────────────────── */}
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Usuarios</h1>
          <p className={styles.subtitle}>Gestiona las cuentas y roles del sistema.</p>
        </div>
        <div className={styles.headerActions}>
          <button
            className={styles.btnSecondary}
            onClick={() => navigate('/usuarios/roles')}
          >
            <i className="ti ti-shield-lock" aria-hidden="true" />
            Gestionar roles
          </button>
          <button
            className={styles.btnPrimary}
            onClick={() => navigate('/usuarios/nuevo')}
          >
            <i className="ti ti-user-plus" aria-hidden="true" />
            Crear usuario
          </button>
        </div>
      </header>

      {/* ── Toolbar ────────────────────────────── */}
      <div className={styles.toolbar}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3, 16px)', flexWrap: 'wrap' }}>
          <div className={styles.tabs}>
            {TABS.map((tab) => (
              <button
                key={tab.value}
                className={`${styles.tab} ${estadoFiltro === tab.value ? styles.tabActive : ''}`}
                onClick={() => setEstadoFiltro(tab.value)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className={styles.searchBox}>
            <i className={`ti ti-search ${styles.searchIcon}`} aria-hidden="true" />
            <input
              type="text"
              className={styles.searchInput}
              placeholder="Buscar por nombre o email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {!loading && !error && (
          <span className={styles.resultCount}>
            {count} {count === 1 ? 'usuario' : 'usuarios'}
          </span>
        )}
      </div>

      {/* ── Tabla ──────────────────────────────── */}
      <div className={styles.card}>
        <UsuarioTable
          usuarios={usuarios}
          loading={loading}
          error={error}
          onRetry={reload}
          onVer={(id) => navigate(`/usuarios/${id}`)}
          onEditar={(id) => navigate(`/usuarios/${id}/editar`)}
          onEliminar={handleEliminar}
          onRecuperar={handleRecuperar}
          onCrearPrimero={() => navigate('/usuarios/nuevo')}
        />

        {!loading && !error && usuarios.length > 0 && totalPages > 1 && (
          <div className={styles.pagination}>
            <span className={styles.pageInfo}>
              Página {page} de {totalPages}
            </span>
            <div className={styles.pageControls}>
              <button
                className={styles.btnSecondary}
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <i className="ti ti-chevron-left" aria-hidden="true" />
              </button>
              <button
                className={styles.btnSecondary}
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                <i className="ti ti-chevron-right" aria-hidden="true" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
