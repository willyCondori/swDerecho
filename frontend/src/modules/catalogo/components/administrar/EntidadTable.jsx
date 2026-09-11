// modules/catalogo/components/administrar/EntidadTable.jsx
import styles from '../../pages/AdministrarCatalogoPage.module.css'

function SkeletonRows({ rows = 4 }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i} className={styles.skeletonRow}>
          <td><div className={styles.skeleton} style={{ width: 200 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 320 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 70 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 60, marginLeft: 'auto' }} /></td>
        </tr>
      ))}
    </>
  )
}

export default function EntidadTable({
  entidades,
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
        <button className={styles.btnSecondary} onClick={onRetry}>Reintentar</button>
      </div>
    )
  }

  if (!loading && entidades.length === 0) {
    return (
      <div className={styles.emptyState}>
        <i className={`ti ti-users ${styles.emptyIcon}`} aria-hidden="true" />
        <p className={styles.emptyText}>Todavía no hay entidades jurídicas registradas.</p>
        <button className={styles.btnPrimary} onClick={onCrearPrimero}>
          <i className="ti ti-plus" aria-hidden="true" /> Nueva entidad
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
          entidades.map((entidad) => {
            const inactiva = !entidad.estado
            return (
              <tr key={entidad.id}>
                <td><span className={styles.itemNombre}>{entidad.nombre}</span></td>
                <td>
                  <span className={styles.itemDescripcion}>
                    {entidad.descripcion || 'Sin descripción'}
                  </span>
                </td>
                <td>
                  <span className={`${styles.badge} ${entidad.estado ? styles.activo : styles.inactivo}`}>
                    {entidad.estado ? 'Activa' : 'Eliminada'}
                  </span>
                </td>
                <td>
                  <div className={styles.actionsCell}>
                    {inactiva ? (
                      <button
                        className={styles.iconBtn}
                        title="Recuperar entidad"
                        onClick={() => onRecuperar(entidad)}
                      >
                        <i className="ti ti-rotate-clockwise" aria-hidden="true" />
                      </button>
                    ) : (
                      <>
                        <button className={styles.iconBtn} title="Editar" onClick={() => onEditar(entidad)}>
                          <i className="ti ti-pencil" aria-hidden="true" />
                        </button>
                        <button className={styles.iconBtn} title="Eliminar" onClick={() => onEliminar(entidad)}>
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
