// modules/catalogo/components/administrar/NormaTable.jsx
import styles from '../../pages/AdministrarCatalogoPage.module.css'

function SkeletonRows({ rows = 4 }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i} className={styles.skeletonRow}>
          <td><div className={styles.skeleton} style={{ width: 260 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 60 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 140 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 70 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 40, marginLeft: 'auto' }} /></td>
        </tr>
      ))}
    </>
  )
}

export default function NormaTable({
  normas,
  loading,
  error,
  busqueda,
  mostrandoEliminadas,
  onRetry,
  onEliminar,
  onRecuperar,
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

  if (!loading && normas.length === 0 && busqueda?.trim()) {
    return (
      <div className={styles.emptyState}>
        <i className={`ti ti-search ${styles.emptyIcon}`} aria-hidden="true" />
        <p className={styles.emptyText}>
          No se encontraron normas para “{busqueda.trim()}”.
        </p>
      </div>
    )
  }

  if (!loading && normas.length === 0) {
    return (
      <div className={styles.emptyState}>
        <i className={`ti ti-books ${styles.emptyIcon}`} aria-hidden="true" />
        <p className={styles.emptyText}>
          {mostrandoEliminadas
            ? 'No hay normas eliminadas.'
            : 'Todavía no hay normas registradas. Se crean al cargar un PDF de artículos.'}
        </p>
      </div>
    )
  }

  return (
    <div className={styles.tableScroll}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Nombre</th>
            <th>Sigla</th>
            <th>Jerarquía</th>
            <th>Estado</th>
            <th aria-label="Acciones" />
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <SkeletonRows />
          ) : (
            normas.map((norma) => (
              <tr key={norma.id}>
                <td><span className={styles.itemNombre}>{norma.nombre}</span></td>
                <td><span className={styles.itemDescripcion}>{norma.sigla || '—'}</span></td>
                <td>
                  <span className={styles.itemDescripcion}>
                    {norma.jerarquia?.nombre || 'Sin jerarquía'}
                  </span>
                </td>
                <td>
                  <span className={`${styles.badge} ${norma.estado ? styles.activo : styles.inactivo}`}>
                    {norma.estado ? 'Activa' : 'Eliminada'}
                  </span>
                </td>
                <td>
                  <div className={styles.actionsCell}>
                    {norma.estado ? (
                      <button className={styles.iconBtn} title="Eliminar" onClick={() => onEliminar(norma)}>
                        <i className="ti ti-trash" aria-hidden="true" />
                      </button>
                    ) : (
                      <button className={styles.iconBtn} title="Recuperar norma" onClick={() => onRecuperar(norma)}>
                        <i className="ti ti-rotate-clockwise" aria-hidden="true" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
