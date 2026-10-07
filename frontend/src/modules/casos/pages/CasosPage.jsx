import ListState from '../../../components/ui/ListState'
import PageHeader from '../../../components/ui/PageHeader'
import Pagination from '../../../components/ui/Pagination'
import SearchField from '../../../components/ui/SearchField'
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
      <PageHeader classes={styles} title="Casos" subtitle="Todos tus casos y el cliente asociado a cada uno.">

          <button
            className={styles.btnSecondary}
            onClick={() => setMostrarFiltros((v) => !v)}
          >
            <i className="ti ti-filter" aria-hidden="true" />
            Filtros
          </button>
          {puedeEscribir && (
            <button className={styles.btnSecondary} onClick={() => navigate('/casos/papelera')}>
              <i className="ti ti-trash" aria-hidden="true" />
              Papelera
            </button>
          )}
          {puedeEscribir && (
            <button className={styles.btnPrimary} onClick={() => navigate('/casos/nuevo')}>
              <i className="ti ti-plus" aria-hidden="true" />
              Nuevo caso
            </button>
          )}

</PageHeader>

      <CasoFiltros
        filtros={filtros}
        onChange={setFiltros}
        onLimpiar={limpiarFiltros}
        visible={mostrarFiltros}
      />

      <div className={styles.toolbar}>
        <SearchField classes={styles} placeholder="Buscar por código o título..." value={filtros.search} onChange={(search) => setFiltros({ search })} />
        {!loading && !error && (
          <span className={styles.resultCount}>
            {count} {count === 1 ? 'caso' : 'casos'}
          </span>
        )}
      </div>

      {!loading && error ? (
        <div className={styles.grid}>
          <ListState classes={styles} icon="ti-wifi-off" text={error} action={<button className={styles.btnSecondary} onClick={reload}>Reintentar</button>} />
        </div>
      ) : !loading && casos.length === 0 ? (
        <div className={styles.grid}>
          <ListState classes={styles} icon="ti-folder-off" text={'No se encontraron casos.'} action={puedeEscribir && (
              <button className={styles.btnPrimary} onClick={() => navigate('/casos/nuevo')}>
                <i className="ti ti-plus" aria-hidden="true" /> Crear primer caso
              </button>
            )} />
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
        <Pagination classes={styles} variant="simple" page={page} totalPages={totalPages} onPageChange={setPage} />
      )}
    </div>
  )
}
