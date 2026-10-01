// modules/catalogo/components/administrar/NormasSection.jsx
// Listado de normas con eliminación lógica y recuperación. Lo comparten la
// pestaña "Normas" de Administrar catálogo y la página /catalogo/normas.
import { useState } from 'react'
import useGestionNormas from '../../hooks/useGestionNormas'
import NormaTable from './NormaTable'
import DocumentosNormaPanel from './DocumentosNormaPanel'
import Pagination from '../../../../components/ui/Pagination'
import styles from '../../pages/AdministrarCatalogoPage.module.css'

const ESTADO_TABS = [
  { value: 'activas', label: 'Activas' },
  { value: 'eliminadas', label: 'Eliminadas' },
]

export default function NormasSection() {
  const {
    normas, loading, error, reload,
    search, setSearch,
    page, setPage, count, totalPages, pageSize,
    estadoFiltro, setEstadoFiltro,
    eliminarNorma, activarNorma,
  } = useGestionNormas()

  const [normaDocumentos, setNormaDocumentos] = useState(null)

  const handleEliminar = async (norma) => {
    if (!window.confirm(`¿Eliminar la norma "${norma.nombre}"? No se borra nada: sus artículos dejarán de verse en el catálogo y de considerarse en el análisis de casos, y volverán a estar disponibles si la recuperas desde la pestaña "Eliminadas".`)) return
    try {
      await eliminarNorma(norma.id)
    } catch (e) {
      window.alert(e?.response?.data?.detail || 'No se pudo eliminar la norma.')
    }
  }

  const handleRecuperar = async (norma) => {
    if (!window.confirm(`¿Recuperar la norma "${norma.nombre}"? Sus artículos volverán a verse en el catálogo y a considerarse en el análisis de casos.`)) return
    try {
      await activarNorma(norma.id)
    } catch (e) {
      window.alert(e?.response?.data?.detail || 'No se pudo recuperar la norma.')
    }
  }

  return (
    <>
      <div className={styles.sectionToolbar}>
        <div className={styles.tabs}>
          {ESTADO_TABS.map((t) => (
            <button
              key={t.value}
              className={`${styles.tab} ${estadoFiltro === t.value ? styles.tabActive : ''}`}
              onClick={() => setEstadoFiltro(t.value)}
              type="button"
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className={styles.searchBox}>
          <i className={`ti ti-search ${styles.searchIcon}`} aria-hidden="true" />
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Buscar norma por nombre o sigla..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className={styles.card}>
        <NormaTable
          normas={normas}
          loading={loading}
          error={error}
          busqueda={search}
          mostrandoEliminadas={estadoFiltro === 'eliminadas'}
          onRetry={reload}
          onEliminar={handleEliminar}
          onRecuperar={handleRecuperar}
          onVerDocumentos={setNormaDocumentos}
        />
        {!loading && !error && (
          <Pagination
            page={page}
            totalPages={totalPages}
            count={count}
            pageSize={pageSize}
            onPageChange={setPage}
            itemLabel="normas"
          />
        )}
      </div>

      {normaDocumentos && (
        <DocumentosNormaPanel
          norma={normaDocumentos}
          onClose={() => setNormaDocumentos(null)}
        />
      )}
    </>
  )
}
