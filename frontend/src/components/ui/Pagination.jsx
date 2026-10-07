import shared from '../../styles/shared.module.css'

function ventana(page, totalPages, max = 5) {
  const mitad = Math.floor(max / 2)
  let inicio = Math.max(1, page - mitad)
  const fin = Math.min(totalPages, inicio + max - 1)
  inicio = Math.max(1, fin - max + 1)
  return Array.from({ length: Math.max(0, fin - inicio + 1) }, (_, i) => inicio + i)
}

/** Numbered or compact navigation, with an optional page-size selector. */
export default function Pagination({ page, totalPages, count = 0, pageSize,
  onPageChange, itemLabel = 'registros', variant = 'numbered', alwaysShow = false,
  firstItem, lastItem, visiblePages, onPageSizeChange, pageSizeOptions = [10, 25, 50],
  pageSizeLabel = 'Registros por página', classes = shared,
}) {
  if (!alwaysShow && (totalPages <= 1 || (variant !== 'simple' && !count))) return null
  const pages = Math.max(1, totalPages)
  const simple = variant === 'simple'
  const buttonClass = simple ? classes.btnSecondary : classes.pageBtn
  const change = (target) => onPageChange(Math.max(1, Math.min(pages, target)))
  const control = (target, disabled, label, icon) => <button type="button" className={buttonClass}
    disabled={disabled} aria-label={label} onClick={() => change(target)}>
    <i className={`ti ${icon}`} aria-hidden="true" /></button>
  return <div className={classes.pagination}>
    <span className={classes.pageInfo}>{simple ? `Página ${page} de ${pages}` :
      `Mostrando ${firstItem ?? (count ? (page - 1) * pageSize + 1 : 0)}–${lastItem ?? Math.min(page * pageSize, count)} de ${count.toLocaleString('es-BO')} ${itemLabel}`}</span>
    <div className={classes.pageControls}>
      {onPageSizeChange && <select className={classes.pageSizeSelect} value={pageSize}
        onChange={(event) => onPageSizeChange(Number(event.target.value))} aria-label={pageSizeLabel}>
        {pageSizeOptions.map((size) => <option key={size} value={size}>{size} / pág.</option>)}
      </select>}
      {!simple && control(1, page <= 1, 'Primera página', 'ti-chevrons-left')}
      {control(page - 1, page <= 1, 'Página anterior', 'ti-chevron-left')}
      {!simple && (visiblePages ?? ventana(page, pages)).map((number) => <button key={number} type="button"
        className={`${classes.pageBtn} ${number === page ? classes.pageBtnActive : ''}`}
        aria-current={number === page ? 'page' : undefined} onClick={() => change(number)}>{number}</button>)}
      {control(page + 1, page >= pages, 'Página siguiente', 'ti-chevron-right')}
      {!simple && control(pages, page >= pages, 'Última página', 'ti-chevrons-right')}
    </div>
  </div>
}
