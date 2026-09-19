// components/ui/Pagination.jsx
import styles from '../../styles/shared.module.css'

// Ventana de números de página alrededor de la actual (máx. `max` botones).
function ventana(page, totalPages, max = 5) {
  const mitad = Math.floor(max / 2)
  let inicio = Math.max(1, page - mitad)
  const fin = Math.min(totalPages, inicio + max - 1)
  inicio = Math.max(1, fin - max + 1)
  return Array.from({ length: fin - inicio + 1 }, (_, i) => inicio + i)
}

export default function Pagination({
  page,
  totalPages,
  count,
  pageSize,
  onPageChange,
  itemLabel = 'registros',
}) {
  if (!count || totalPages <= 1) return null

  const primero = (page - 1) * pageSize + 1
  const ultimo = Math.min(page * pageSize, count)

  return (
    <div className={styles.pagination}>
      <span className={styles.pageInfo}>
        Mostrando {primero}–{ultimo} de {count.toLocaleString('es-BO')} {itemLabel}
      </span>

      <div className={styles.pageControls}>
        <button
          type="button"
          className={styles.pageBtn}
          onClick={() => onPageChange(1)}
          disabled={page <= 1}
          aria-label="Primera página"
        >
          <i className="ti ti-chevrons-left" aria-hidden="true" />
        </button>
        <button
          type="button"
          className={styles.pageBtn}
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page <= 1}
          aria-label="Página anterior"
        >
          <i className="ti ti-chevron-left" aria-hidden="true" />
        </button>

        {ventana(page, totalPages).map((p) => (
          <button
            key={p}
            type="button"
            className={`${styles.pageBtn} ${p === page ? styles.pageBtnActive : ''}`}
            onClick={() => onPageChange(p)}
            aria-current={p === page ? 'page' : undefined}
          >
            {p}
          </button>
        ))}

        <button
          type="button"
          className={styles.pageBtn}
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page >= totalPages}
          aria-label="Página siguiente"
        >
          <i className="ti ti-chevron-right" aria-hidden="true" />
        </button>
        <button
          type="button"
          className={styles.pageBtn}
          onClick={() => onPageChange(totalPages)}
          disabled={page >= totalPages}
          aria-label="Última página"
        >
          <i className="ti ti-chevrons-right" aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}
