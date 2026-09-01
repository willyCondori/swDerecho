// modules/usuarios/components/RolTable.jsx
import styles from '../pages/RolesPage.module.css'

const ROLES_SISTEMA = ['administrador']

function SkeletonRows({ rows = 4 }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i} className={styles.skeletonRow}>
          <td><div className={styles.skeleton} style={{ width: 140 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 260 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 70 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 60, marginLeft: 'auto' }} /></td>
        </tr>
      ))}
    </>
  )
}

export default function RolTable({
  roles,
  loading,
  error,
  onRetry,
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

  if (!loading && roles.length === 0) {
    return (
      <div className={styles.emptyState}>
        <i className={`ti ti-shield-lock ${styles.emptyIcon}`} aria-hidden="true" />
        <p className={styles.emptyText}>No se encontraron roles.</p>
        <button className={styles.btnPrimary} onClick={onCrearPrimero}>
          <i className="ti ti-shield-plus" aria-hidden="true" /> Nuevo rol
        </button>
      </div>
    )
  }

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th>Nombre</th>
          <th>Descripción</th>
          <th>Estado</th>
          <th aria-label="Acciones" />
        </tr>
      </thead>
      <tbody>
        {loading ? (
          <SkeletonRows />
        ) : (
          roles.map((rol) => {
            const inactivo = !rol.estado
            const esRolSistema = ROLES_SISTEMA.includes(rol.nombre?.trim().toLowerCase())
            return (
              <tr key={rol.id}>
                <td>
                  <div className={styles.rolNombre}>
                    {rol.nombre}
                    {esRolSistema && (
                      <span className={styles.badgePurple} title="Rol del sistema, no se puede desactivar">
                        <i className="ti ti-lock" aria-hidden="true" /> sistema
                      </span>
                    )}
                  </div>
                </td>
                <td>
                  <span className={styles.rolDescripcion}>
                    {rol.descripcion || 'Sin descripción'}
                  </span>
                </td>
                <td>
                  <span className={`${styles.badge} ${rol.estado ? styles.activo : styles.inactivo}`}>
                    {rol.estado ? 'Activo' : 'Eliminado'}
                  </span>
                </td>
                <td>
                  <div className={styles.actionsCell}>
                    {inactivo ? (
                      <button
                        className={styles.iconBtn}
                        title="Recuperar rol"
                        onClick={() => onRecuperar(rol)}
                      >
                        <i className="ti ti-rotate-clockwise" aria-hidden="true" />
                      </button>
                    ) : (
                      <>
                        <button
                          className={styles.iconBtn}
                          title="Editar"
                          onClick={() => onEditar(rol)}
                        >
                          <i className="ti ti-pencil" aria-hidden="true" />
                        </button>
                        <button
                          className={styles.iconBtn}
                          title={esRolSistema ? 'El rol Administrador no puede desactivarse' : 'Eliminar'}
                          disabled={esRolSistema}
                          onClick={() => onEliminar(rol)}
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
