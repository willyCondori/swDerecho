import { dialogs } from '../../../../components/ui/dialogs'
import FilterTabs from '../../../../components/ui/FilterTabs'
import SearchField from '../../../../components/ui/SearchField'
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
    if (!await dialogs.confirm(`¿Eliminar la norma "${norma.nombre}"? No se borra nada: sus artículos dejarán de verse en el catálogo y de considerarse en el análisis de casos, y volverán a estar disponibles si la recuperas desde la pestaña "Eliminadas".`)) return
    try {
      await eliminarNorma(norma.id)
    } catch (e) {
      dialogs.alert(e?.response?.data?.detail || 'No se pudo eliminar la norma.')
    }
  }

  const handleRecuperar = async (norma) => {
    if (!await dialogs.confirm(`¿Recuperar la norma "${norma.nombre}"? Sus artículos volverán a verse en el catálogo y a considerarse en el análisis de casos.`)) return
    try {
      await activarNorma(norma.id)
    } catch (e) {
      dialogs.alert(e?.response?.data?.detail || 'No se pudo recuperar la norma.')
    }
  }

  return (
    <>
      <div className={styles.sectionToolbar}>
        <FilterTabs classes={styles} options={ESTADO_TABS} value={estadoFiltro} onChange={setEstadoFiltro} />
        <SearchField classes={styles} placeholder="Buscar norma por nombre o sigla..." value={search} onChange={setSearch} />
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
