import Pagination from '../../../../components/ui/Pagination'
import useLocalPagination from '../../../../hooks/useLocalPagination'
import styles from './Normativa.module.css'

/** Normalized rows let preview and catalog share the same disposition table. */
export default function DisposicionesList({ rows, showNorma = false, renderLinks, paginate = true }) {
  const { page, pageSize, totalPages, setPage, setPageSize, visibleRows } = useLocalPagination(rows)
  const displayed = paginate ? visibleRows : rows
  return <><div className={styles.tablaContenedor}>
    <table className={styles.tabla} aria-label="Disposiciones finales, derogatorias y abrogatorias">
      <thead><tr>{showNorma && <th>Norma</th>}<th>Tipo</th><th>Disposición</th><th>Texto</th></tr></thead>
      <tbody>{displayed.map((row) => <tr key={row.key}>
        {showNorma && <td>{row.norma}</td>}<td>{row.tipo}</td><td>{row.numero}</td>
        <td>{renderLinks?.(row)}<details><summary>Ver disposición</summary>
          <p style={{ whiteSpace: 'pre-wrap' }}>{row.texto}</p>
        </details></td>
      </tr>)}</tbody>
    </table>
  </div>
    {paginate && rows.length > 0 && <Pagination page={page} pageSize={pageSize} totalPages={totalPages}
      count={rows.length} onPageChange={setPage} onPageSizeChange={setPageSize} alwaysShow
      itemLabel="disposiciones" pageSizeLabel="Disposiciones por página" />}
  </>
}
