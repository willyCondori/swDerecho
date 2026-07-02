// modules/catalogo/components/articulos/Pagination.jsx
import styles from '../../pages/articulos/VerArticulos.module.css'

const PAGE_SIZES = [10, 25, 50]

export default function Pagination({
  page, totalPages, totalCount,
  firstItem, lastItem,
  pageSize, onPageSizeChange,
  onPageChange, visiblePages,
}) {
  return (
    <div className={styles.pagination}>
      <span className={styles.paginationInfo}>
        Mostrando {firstItem}–{lastItem} de {totalCount.toLocaleString('es-BO')} artículos
      </span>

      <div className={styles.paginationControls}>
        <select
          className={styles.pageSizeSelect}
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          aria-label="Artículos por página"
        >
          {PAGE_SIZES.map((s) => (
            <option key={s} value={s}>{s} / pág.</option>
          ))}
        </select>

        <button
          className={styles.pageBtn}
          onClick={() => onPageChange(1)}
          disabled={page === 1}
          aria-label="Primera página"
        >
          <i className="ti ti-chevrons-left" aria-hidden="true" />
        </button>

        <button
          className={styles.pageBtn}
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page === 1}
          aria-label="Página anterior"
        >
          <i className="ti ti-chevron-left" aria-hidden="true" />
        </button>

        {visiblePages.map((p) => (
          <button
            key={p}
            className={`${styles.pageBtn} ${p === page ? styles.active : ''}`}
            onClick={() => onPageChange(p)}
            aria-current={p === page ? 'page' : undefined}
          >
            {p}
          </button>
        ))}

        <button
          className={styles.pageBtn}
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page === totalPages}
          aria-label="Página siguiente"
        >
          <i className="ti ti-chevron-right" aria-hidden="true" />
        </button>

        <button
          className={styles.pageBtn}
          onClick={() => onPageChange(totalPages)}
          disabled={page === totalPages}
          aria-label="Última página"
        >
          <i className="ti ti-chevrons-right" aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}