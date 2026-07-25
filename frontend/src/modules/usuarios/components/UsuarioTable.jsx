// modules/usuarios/components/UsuarioTable.jsx
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

function SkeletonRows({ rows = 5 }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i} className={styles.skeletonRow}>
          <td><div className={styles.skeleton} style={{ width: 180 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 100 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 70 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 90 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 60, marginLeft: 'auto' }} /></td>
        </tr>
      ))}
    </>
  )
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
  if (!loading && error) {
    return (
      <div className={styles.emptyState}>
        <i className={`ti ti-wifi-off ${styles.emptyIcon}`} aria-hidden="true" />
        <p className={styles.emptyText}>{error}</p>
        <button className={styles.btnSecondary} onClick={onRetry}>
          Reintentar
        </button>
      </div>
    )
  }

  if (!loading && usuarios.length === 0) {
    return (
      <div className={styles.emptyState}>
        <i className={`ti ti-users ${styles.emptyIcon}`} aria-hidden="true" />
        <p className={styles.emptyText}>No se encontraron usuarios.</p>
        <button className={styles.btnPrimary} onClick={onCrearPrimero}>
          <i className="ti ti-user-plus" aria-hidden="true" /> Crear usuario
        </button>
      </div>
    )
  }

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th>Usuario</th>
          <th>Rol</th>
          <th>Estado</th>
          <th aria-label="Acciones" />
        </tr>
      </thead>
      <tbody>
        {loading ? (
          <SkeletonRows />
        ) : (
          usuarios.map((usuario) => {
            const inactivo = !usuario.estado
            return (
              <tr key={usuario.id} onClick={() => onVer(usuario.id)}>
                <td>
                  <div className={styles.userCell}>
                    <span className={styles.avatar}>
                      {getIniciales(usuario)}
                    </span>

                    <div>
                      <div className={styles.userName}>
                        {getNombreCompleto(usuario)}
                      </div>

                      <div className={styles.userEmail}>
                        {usuario.perfil?.telefono || 'Sin teléfono'}
                      </div>
                    </div>
                  </div>
                </td>
                <td>
                  <span className={`${styles.badge} ${styles.badgeRol}`}>
                    {usuario.rol?.nombre || usuario.rol || 'Sin rol'}
                  </span>
                </td>
                <td>
                  <span className={`${styles.badge} ${usuario.estado ? styles.activo : styles.inactivo}`}>
                    {usuario.estado ? 'Activo' : 'Eliminado'}
                  </span>
                </td>
                <td>
                  <div className={styles.actionsCell} onClick={(e) => e.stopPropagation()}>
                    {inactivo ? (
                      <button
                        className={styles.iconBtn}
                        title="Recuperar usuario"
                        onClick={() => onRecuperar(usuario)}
                      >
                        <i className="ti ti-rotate-clockwise" aria-hidden="true" />
                      </button>
                    ) : (
                      <>
                        <button
                          className={styles.iconBtn}
                          title="Editar"
                          onClick={() => onEditar(usuario.id)}
                        >
                          <i className="ti ti-pencil" aria-hidden="true" />
                        </button>
                        <button
                          className={styles.iconBtn}
                          title="Eliminar"
                          onClick={() => onEliminar(usuario)}
                        >
                          <i className="ti ti-trash" aria-hidden="true" />
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            )
          })
        )}
      </tbody>
    </table>
  )
}