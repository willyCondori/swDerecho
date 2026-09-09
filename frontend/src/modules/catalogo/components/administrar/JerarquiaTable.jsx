// modules/catalogo/components/administrar/JerarquiaTable.jsx
import styles from '../../pages/AdministrarCatalogoPage.module.css'

function SkeletonRows({ rows = 4 }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i} className={styles.skeletonRow}>
          <td><div className={styles.skeleton} style={{ width: 50 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 220 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 60, marginLeft: 'auto' }} /></td>
        </tr>
      ))}
    </>
  )
}

export default function JerarquiaTable({ jerarquias, loading, error, onRetry, onEditar, onEliminar, onCrearPrimero }) {
  if (!loading && error) {
    return (
      <div className={styles.emptyState}>
        <i className={`ti ti-wifi-off ${styles.emptyIcon}`} aria-hidden="true" />
        <p className={styles.emptyText}>{error}</p>
        <button className={styles.btnSecondary} onClick={onRetry}>Reintentar</button>
      </div>
    )
  }

  if (!loading && jerarquias.length === 0) {
    return (
      <div className={styles.emptyState}>
        <i className={`ti ti-stack-2 ${styles.emptyIcon}`} aria-hidden="true" />
        <p className={styles.emptyText}>Todavía no hay jerarquías normativas registradas.</p>
        <button className={styles.btnPrimary} onClick={onCrearPrimero}>
          <i className="ti ti-plus" aria-hidden="true" /> Nueva jerarquía
        </button>
      </div>
    )
  }

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th>Nivel</th>
          <th>Nombre</th>
          <th aria-label="Acciones" />
        </tr>
      </thead>
      <tbody>
        {loading ? (
          <SkeletonRows />
        ) : (
          jerarquias.map((j) => (
            <tr key={j.id}>
              <td><span className={styles.badge}>{j.nivel}</span></td>
              <td><span className={styles.itemNombre}>{j.nombre}</span></td>
              <td>
                <div className={styles.actionsCell}>
                  <button className={styles.iconBtn} title="Editar" onClick={() => onEditar(j)}>
                    <i className="ti ti-pencil" aria-hidden="true" />
                  </button>
                  <button className={styles.iconBtn} title="Eliminar" onClick={() => onEliminar(j)}>
                    <i className="ti ti-trash" aria-hidden="true" />
                  </button>
                </div>
              </td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  )
}
