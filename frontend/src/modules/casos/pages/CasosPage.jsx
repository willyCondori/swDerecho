// modules/casos/pages/CasosPage.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useCasos from '../hooks/useCasos'
import useAuthStore from '../../auth/store/authStore'
import CasoCard from '../components/CasoCard'
import CasoFiltros from '../components/CasoFiltros'
import styles from './CasosPage.module.css'

export default function CasosPage() {
  const navigate = useNavigate()
  const puedeEscribir = useAuthStore((s) => s.puedeEscribir())
  const [mostrarFiltros, setMostrarFiltros] = useState(false)
  const {
    casos, loading, error, page, setPage, totalPages, count,
    filtros, setFiltros, limpiarFiltros, reload,
  } = useCasos()

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Casos</h1>
          <p className={styles.subtitle}>Todos tus casos y el cliente asociado a cada uno.</p>
        </div>
        <div className={styles.headerActions}>
          <button
            className={styles.btnSecondary}
            onClick={() => setMostrarFiltros((v) => !v)}
          >
            <i className="ti ti-filter" aria-hidden="true" />
            Filtros
          </button>
          {puedeEscribir && (
            <button className={styles.btnPrimary} onClick={() => navigate('/casos/nuevo')}>
              <i className="ti ti-plus" aria-hidden="true" />
              Nuevo caso
            </button>
          )}
        </div>
      </header>

      <CasoFiltros
        filtros={filtros}
        onChange={setFiltros}
        onLimpiar={limpiarFiltros}
        visible={mostrarFiltros}
      />

      <div className={styles.toolbar}>
        <div className={styles.searchBox}>
          <i className={`ti ti-search ${styles.searchIcon}`} aria-hidden="true" />
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Buscar por código o título..."
            value={filtros.search}
            onChange={(e) => setFiltros({ search: e.target.value })}
          />
        </div>
        {!loading && !error && (
          <span className={styles.resultCount}>
            {count} {count === 1 ? 'caso' : 'casos'}
          </span>
        )}
      </div>

      {!loading && error ? (
        <div className={styles.grid}>
          <div className={styles.emptyState}>
            <i className={`ti ti-wifi-off ${styles.emptyIcon}`} aria-hidden="true" />
            <p className={styles.emptyText}>{error}</p>
            <button className={styles.btnSecondary} onClick={reload}>Reintentar</button>
          </div>
        </div>
      ) : !loading && casos.length === 0 ? (
        <div className={styles.grid}>
          <div className={styles.emptyState}>
            <i className={`ti ti-folder-off ${styles.emptyIcon}`} aria-hidden="true" />
            <p className={styles.emptyText}>No se encontraron casos.</p>
            {puedeEscribir && (
              <button className={styles.btnPrimary} onClick={() => navigate('/casos/nuevo')}>
                <i className="ti ti-plus" aria-hidden="true" /> Crear primer caso
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className={styles.grid}>
          {loading ? (
            Array.from({ length: 6 }).map((_, i) => <div key={i} className={styles.skeletonCard} />)
          ) : (
            casos.map((caso) => (
              <CasoCard key={caso.id} caso={caso} onVerDetalle={(id) => navigate(`/casos/${id}`)} />
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