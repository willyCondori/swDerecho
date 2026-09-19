// modules/casos/pages/PapeleraCasosPage.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import usePapeleraCasos from '../hooks/usePapeleraCasos'
import EtapaBadge from '../components/EtapaBadge'
import { formatFechaHora } from '../utils/etapas'
import styles from './PapeleraCasosPage.module.css'

function textoEliminacion(caso) {
  if (!caso.eliminado_at) return 'Eliminado antes de que existiera la papelera (fecha desconocida)'
  const cuando = formatFechaHora(caso.eliminado_at)
  return caso.eliminado_por_nombre
    ? `Eliminado el ${cuando} por ${caso.eliminado_por_nombre}`
    : `Eliminado el ${cuando}`
}

export default function PapeleraCasosPage() {
  const navigate = useNavigate()
  const [errorRestaurar, setErrorRestaurar] = useState('')
  const [restaurado, setRestaurado] = useState('')
  const {
    casos, loading, error, page, setPage, totalPages, count,
    search, setSearch, restaurar, restaurandoId, reload,
  } = usePapeleraCasos()

  const handleRestaurar = async (caso) => {
    if (!window.confirm(`¿Restaurar el caso ${caso.codigo}? Volverá a aparecer en la lista de casos.`)) return
    setErrorRestaurar('')
    setRestaurado('')
    const res = await restaurar(caso.id)
    if (res.ok) setRestaurado(`El caso ${caso.codigo} fue restaurado.`)
    else setErrorRestaurar(res.error)
  }

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Papelera de casos</h1>
          <p className={styles.subtitle}>
            Casos eliminados. Restauralos para devolverlos a la lista de casos con todo su historial.
          </p>
        </div>
        <div className={styles.headerActions}>
          <button className={styles.btnSecondary} onClick={() => navigate('/casos')}>
            <i className="ti ti-arrow-left" aria-hidden="true" />
            Volver a casos
          </button>
        </div>
      </header>

      <div className={styles.toolbar}>
        <div className={styles.searchBox}>
          <i className={`ti ti-search ${styles.searchIcon}`} aria-hidden="true" />
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Buscar por código o título..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        {!loading && !error && (
          <span className={styles.resultCount}>
            {count} {count === 1 ? 'caso eliminado' : 'casos eliminados'}
          </span>
        )}
      </div>

      {errorRestaurar && <div className={styles.errorBanner}>{errorRestaurar}</div>}
      {restaurado && <div className={styles.resultCount} role="status">{restaurado}</div>}

      {!loading && error ? (
        <div className={styles.emptyState}>
          <i className={`ti ti-wifi-off ${styles.emptyIcon}`} aria-hidden="true" />
          <p className={styles.emptyText}>{error}</p>
          <button className={styles.btnSecondary} onClick={reload}>Reintentar</button>
        </div>
      ) : !loading && casos.length === 0 ? (
        <div className={styles.emptyState}>
          <i className={`ti ti-trash-off ${styles.emptyIcon}`} aria-hidden="true" />
          <p className={styles.emptyText}>
            {search ? 'No se encontraron casos eliminados con esa búsqueda.' : 'La papelera está vacía.'}
          </p>
        </div>
      ) : (
        <div className={styles.lista}>
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => <div key={i} className={styles.fila} style={{ height: 88 }} />)
          ) : (
            casos.map((caso) => (
              <div key={caso.id} className={styles.fila}>
                <div className={styles.info}>
                  <span className={styles.codigo}>{caso.codigo}</span>
                  <h3 className={styles.tituloCaso}>{caso.titulo}</h3>
                  <div className={styles.meta}>
                    <span className={styles.metaItem}>
                      <i className="ti ti-user" aria-hidden="true" /> {caso.cliente_nombre}
                    </span>
                    {caso.rama_detectada && (
                      <span className={styles.metaItem}>
                        <i className="ti ti-category" aria-hidden="true" /> {caso.rama_detectada}
                      </span>
                    )}
                    <EtapaBadge etapa={caso.etapa} label={caso.etapa_display} />
                  </div>
                  <span className={styles.eliminado}>{textoEliminacion(caso)}</span>
                </div>
                <button
                  type="button"
                  className={styles.btnPrimary}
                  onClick={() => handleRestaurar(caso)}
                  disabled={restaurandoId === caso.id}
                >
                  <i className="ti ti-restore" aria-hidden="true" />{' '}
                  {restaurandoId === caso.id ? 'Restaurando...' : 'Restaurar'}
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {!loading && !error && casos.length > 0 && totalPages > 1 && (
        <div className={styles.pagination}>
          <span className={styles.pageInfo}>Página {page} de {totalPages}</span>
          <div className={styles.pageControls}>
            <button className={styles.btnSecondary} disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
              <i className="ti ti-chevron-left" aria-hidden="true" />
            </button>
            <button className={styles.btnSecondary} disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>
              <i className="ti ti-chevron-right" aria-hidden="true" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
