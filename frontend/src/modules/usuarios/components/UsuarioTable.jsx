// modules/usuarios/components/UsuarioTable.jsx
import DataTable from '../../../components/ui/DataTable'
import styles from '../pages/UsuariosPage.module.css'

function getIniciales(usuario) {
  const nombre = usuario.perfil?.nombres ?? ''
  const apellido = usuario.perfil?.apellidos ?? ''

  const iniciales = `${nombre.charAt(0)}${apellido.charAt(0)}`.toUpperCase()

  return iniciales || usuario.usuario?.charAt(0).toUpperCase() || '?'
}

function getNombreCompleto(usuario) {
  const nombre = usuario.perfil?.nombres ?? ''
  const apellido = usuario.perfil?.apellidos ?? ''

  const completo = `${nombre} ${apellido}`.trim()

  return completo || usuario.usuario
}

export default function UsuarioTable({
  usuarios,
  loading,
  error,
  onRetry,
  onVer,
  onEditar,
  onEliminar,
  onRecuperar,
  onCrearPrimero,
}) {
  const columns = [
    {
      key: 'usuario',
      header: 'Usuario',
      skeletonWidth: 180,
      render: (usuario) => (
        <div className={styles.userCell}>
          <span className={styles.avatar}>{getIniciales(usuario)}</span>
          <div>
            <div className={styles.userName}>{getNombreCompleto(usuario)}</div>
            <div className={styles.userEmail}>{usuario.perfil?.telefono || 'Sin teléfono'}</div>
          </div>
        </div>
      ),
    },
    {
      key: 'rol',
      header: 'Rol',
      skeletonWidth: 100,
      render: (usuario) => (
        <span className={`${styles.badge} ${styles.badgeRol}`}>
          {usuario.rol?.nombre || usuario.rol || 'Sin rol'}
        </span>
      ),
    },
    {
      key: 'estado',
      header: 'Estado',
      skeletonWidth: 70,
      render: (usuario) => (
        <span className={`${styles.badge} ${usuario.estado ? styles.activo : styles.inactivo}`}>
          {usuario.estado ? 'Activo' : 'Eliminado'}
        </span>
      ),
    },
    {
      key: 'acciones',
      ariaLabel: 'Acciones',
      actions: true,
      render: (usuario) => (
        usuario.estado ? (
          <>
            <button className={styles.iconBtn} title="Editar" onClick={() => onEditar(usuario.id)}>
              <i className="ti ti-pencil" aria-hidden="true" />
            </button>
            <button className={styles.iconBtn} title="Eliminar" onClick={() => onEliminar(usuario)}>
              <i className="ti ti-trash" aria-hidden="true" />
            </button>
          </>
        ) : (
          <button className={styles.iconBtn} title="Recuperar usuario" onClick={() => onRecuperar(usuario)}>
            <i className="ti ti-rotate-clockwise" aria-hidden="true" />
          </button>
        )
      ),
    },
  ]

  return (
    <DataTable
      columns={columns}
      rows={usuarios}
      loading={loading}
      error={error}
      onRetry={onRetry}
      onRowClick={(usuario) => onVer(usuario.id)}
      empty={{
        icon: 'ti-users',
        text: 'No se encontraron usuarios.',
        action: (
          <button className={styles.btnPrimary} onClick={onCrearPrimero}>
            <i className="ti ti-user-plus" aria-hidden="true" /> Crear usuario
          </button>
        ),
      }}
    />
  )
}
