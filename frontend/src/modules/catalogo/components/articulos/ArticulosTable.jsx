// modules/catalogo/components/articulos/ArticulosTable.jsx
import SkeletonRows from './SkeletonRows'
import ArticuloRow from './ArticuloRow'
import styles from '../../pages/articulos/VerArticulos.module.css'

function SortIcon({ campo, ordering, orderDir }) {
  if (ordering !== campo) return <i className="ti ti-arrows-sort" style={{ opacity: 0.3 }} />
  return orderDir === 'asc'
    ? <i className="ti ti-sort-ascending" />
    : <i className="ti ti-sort-descending" />
}

export default function ArticulosTable({
  articulos, loading, error, pageSize,
  ordering, orderDir, onSort,
  expanded, onToggleExpand,
  hayFiltros, onReintentar, onLimpiarFiltros, onCargarPdf,
}) {
  return (
    <div className={styles.tableScroll}>
      <table className={styles.table} aria-label="Catálogo de artículos jurídicos">
        <thead className={styles.thead}>
          <tr>
            <th className={`${styles.th} ${styles.sortable}`} onClick={() => onSort('numero_articulo')}>
              Artículo
              <span className={styles.sortIcon}>
                <SortIcon campo="numero_articulo" ordering={ordering} orderDir={orderDir} />
              </span>
            </th>
            <th className={styles.th}>Título / Contenido</th>
            <th className={`${styles.th} ${styles.sortable}`} onClick={() => onSort('rama')}>
              Rama
              <span className={styles.sortIcon}>
                <SortIcon campo="rama" ordering={ordering} orderDir={orderDir} />
              </span>
            </th>
            <th className={`${styles.th} ${styles.sortable}`} onClick={() => onSort('norma')}>
              Norma
              <span className={styles.sortIcon}>
                <SortIcon campo="norma" ordering={ordering} orderDir={orderDir} />
              </span>
            </th>
            <th
              className={`${styles.th} ${styles.sortable}`}
              onClick={() => onSort('jerarquia_normativa')}
              title="Jerarquía normativa (Constitución=1.0, Código=0.8)"
            >
              Jerarquía
              <span className={styles.sortIcon}>
                <SortIcon campo="jerarquia_normativa" ordering={ordering} orderDir={orderDir} />
              </span>
            </th>
            <th
              className={`${styles.th} ${styles.sortable} ${styles.center}`}
              onClick={() => onSort('-frecuencia_historica')}
              title="Veces aplicado en casos anteriores"
            >
              Uso
              <span className={styles.sortIcon}>
                <SortIcon campo="-frecuencia_historica" ordering={ordering} orderDir={orderDir} />
              </span>
            </th>
          </tr>
        </thead>

        <tbody>
          {loading ? (
            <SkeletonRows cols={6} rows={pageSize > 10 ? 10 : pageSize} />
          ) : error ? (
            <tr className={styles.tr}>
              <td colSpan={6} className={styles.td}>
                <div className={styles.emptyState}>
                  <i className={`ti ti-wifi-off ${styles.emptyIcon}`} aria-hidden="true" />
                  <p className={styles.emptyTitle}>Error de conexión</p>
                  <p className={styles.emptyText}>{error}</p>
                  <button className={styles.btnSecondary} onClick={onReintentar}>
                    <i className="ti ti-refresh" aria-hidden="true" /> Reintentar
                  </button>
                </div>
              </td>
            </tr>
          ) : articulos.length === 0 ? (
            <tr className={styles.tr}>
              <td colSpan={6} className={styles.td}>
                <div className={styles.emptyState}>
                  <i className={`ti ti-article-off ${styles.emptyIcon}`} aria-hidden="true" />
                  <p className={styles.emptyTitle}>
                    {hayFiltros ? 'Sin resultados' : 'Catálogo vacío'}
                  </p>
                  <p className={styles.emptyText}>
                    {hayFiltros
                      ? 'Ningún artículo coincide con los filtros aplicados.'
                      : 'Aún no hay artículos cargados. Sube un PDF para comenzar.'}
                  </p>
                  {hayFiltros ? (
                    <button className={styles.btnSecondary} onClick={onLimpiarFiltros}>
                      Limpiar filtros
                    </button>
                  ) : (
                    <button className={styles.btnPrimary} onClick={onCargarPdf}>
                      <i className="ti ti-file-upload" aria-hidden="true" /> Cargar PDF
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ) : (
            articulos.map((art) => (
              <ArticuloRow
                key={art.id}
                articulo={art}
                isExpanded={expanded.has(art.id)}
                onToggleExpand={onToggleExpand}
              />
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}