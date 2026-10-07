import DisposicionesList from './DisposicionesList'
import Pagination from '../../../../components/ui/Pagination'
import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import api from '../../../../api/axiosInstance'
import styles from './Normativa.module.css'

const PAGE_SIZE = 10

export default function DisposicionesTable({ normaId, ramaId }) {
  const filtersKey = JSON.stringify([normaId || '', ramaId || ''])
  const [navigation, setNavigation] = useState({ filtersKey, page: 1 })
  const page = navigation.filtersKey === filtersKey ? navigation.page : 1
  const setPage = (next) => setNavigation({ filtersKey, page: next })
  const [result, setResult] = useState(null)
  useEffect(() => {
    let active = true
    api.get('/api/catalogo/disposiciones/', { params: { norma_id: normaId || undefined,
      rama_id: ramaId || undefined, page, page_size: PAGE_SIZE } })
      .then(({ data }) => {
        if (active) setResult({ filtersKey, page, rows: data.results || data,
          count: data.count ?? data.length ?? 0, error: '' })
      }).catch((error) => {
        if (!active) return
        if (error.response?.status === 404 && page > 1) {
          setNavigation({ filtersKey, page: page - 1 })
        } else setResult({ filtersKey, page, rows: [], count: 0,
          error: 'No se pudieron consultar las disposiciones.' })
      })
    return () => { active = false }
  }, [normaId, ramaId, filtersKey, page])
  const current = result?.filtersKey === filtersKey && result.page === page
  const loading = !current
  const rows = current ? result.rows : []
  const count = current ? result.count : 0
  const error = current ? result.error : ''
  return <section className={styles.panel} aria-label="Disposiciones del catálogo">
    <h2>Disposiciones finales, derogatorias y abrogatorias</h2>
    {loading && <p role="status">Consultando disposiciones…</p>}
    {error && <p role="alert">{error}</p>}
    <DisposicionesList paginate={false} showNorma rows={rows.map((d) => ({ key: d.id, norma: d.norma_nombre,
      tipo: d.tipo, numero: d.numero, texto: d.contenido, normaId: d.norma_id }))}
      renderLinks={(row) => <Link to={`/catalogo/avisos?fuente_norma=${row.normaId}`}>Consultar avisos de la norma</Link>} />
    {!loading && !rows.length && !error && <p>No hay disposiciones cargadas para estos filtros.</p>}
    {!loading && !error && <Pagination page={page} totalPages={Math.max(1, Math.ceil(count / PAGE_SIZE))}
      count={count} pageSize={PAGE_SIZE} onPageChange={setPage} itemLabel="disposiciones" />}
  </section>
}
