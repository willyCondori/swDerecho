import { dialogs } from '../../../components/ui/dialogs'
import PageHeader from '../../../components/ui/PageHeader'
import Pagination from '../../../components/ui/Pagination'
import FilterTabs from '../../../components/ui/FilterTabs'
import SearchField from '../../../components/ui/SearchField'
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
    if (!await dialogs.confirm(`¿Eliminar a ${nombre}? Podrás recuperarlo luego desde la pestaña "Eliminados".`)) return
    try {
      await eliminarUsuario(usuario.id)
    } catch (e) {
      dialogs.alert(e?.response?.data?.detail || 'No se pudo eliminar el usuario.')
    }
  }

  const handleRecuperar = async (usuario) => {
    const nombre = usuario.perfil?.nombres || usuario.usuario || 'este usuario'
    if (!await dialogs.confirm(`¿Recuperar a ${nombre}? Volverá a poder iniciar sesión.`)) return
    try {
      await recuperarUsuario(usuario.id)
    } catch (e) {
      dialogs.alert(e?.response?.data?.detail || 'No se pudo recuperar el usuario.')
    }
  }

  return (
    <div className={styles.root}>
      {/* ── Encabezado ─────────────────────────── */}
      <PageHeader classes={styles} title="Usuarios" subtitle="Gestiona las cuentas y roles del sistema.">

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

</PageHeader>

      {/* ── Toolbar ────────────────────────────── */}
      <div className={styles.toolbar}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3, 16px)', flexWrap: 'wrap' }}>
          <FilterTabs classes={styles} options={TABS} value={estadoFiltro} onChange={setEstadoFiltro} />

          <SearchField classes={styles} placeholder="Buscar por nombre o email..." value={search} onChange={setSearch} />
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
          <Pagination classes={styles} variant="simple" page={page} totalPages={totalPages} onPageChange={setPage} />
        )}
      </div>
    </div>
  )
}
