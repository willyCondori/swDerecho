// modules/catalogo/pages/articulos/VerArticulos.jsx
import { useNavigate } from 'react-router-dom'
import { useCatalogoArticulos } from '../../hooks/useCatalogoArticulos'
import CatalogoHeader from '../../components/articulos/CatalogoHeader'
import StatsRow from '../../components/articulos/StatsRow'
import FiltersBar from '../../components/articulos/FiltersBar'
import ArticulosTable from '../../components/articulos/ArticulosTable'
import Pagination from '../../components/articulos/Pagination'
import styles from './VerArticulos.module.css'

export default function VerArticulos() {
  const navigate = useNavigate()
  const {
    ramas, normas,
    search, setSearch,
    ramaId, setRamaId,
    normaId, setNormaId,
    ordering, orderDir, handleSort,
    page, setPage, pageSize, setPageSize,
    articulos, totalCount, totalPages, loading, error,
    expanded, toggleExpand,
    hayFiltros, firstItem, lastItem, visiblePages,
    resetFiltros, recargar,
  } = useCatalogoArticulos()

  const irACargarPdf = () => navigate('/catalogo/cargar')

  return (
    <div className={styles.root}>
      <CatalogoHeader
        totalCount={totalCount}
        onRecargar={recargar}
        onCargarPdf={irACargarPdf}
      />

      <StatsRow
        totalCount={totalCount}
        totalNormas={normas.length}
        totalRamas={ramas.length}
        pageSize={pageSize}
        mostrarPageSize={!hayFiltros && totalCount > 0}
      />

      <FiltersBar
        search={search}
        onSearchChange={setSearch}
        ramaId={ramaId}
        onRamaChange={setRamaId}
        ramas={ramas}
        normaId={normaId}
        onNormaChange={setNormaId}
        normas={normas}
        hayFiltros={hayFiltros}
        totalCount={totalCount}
        onReset={resetFiltros}
      />

      <div className={styles.tableWrapper}>
        <ArticulosTable
          articulos={articulos}
          loading={loading}
          error={error}
          pageSize={pageSize}
          ordering={ordering}
          orderDir={orderDir}
          onSort={handleSort}
          expanded={expanded}
          onToggleExpand={toggleExpand}
          hayFiltros={hayFiltros}
          onReintentar={recargar}
          onLimpiarFiltros={resetFiltros}
          onCargarPdf={irACargarPdf}
        />

        {!loading && totalCount > 0 && (
          <Pagination
            page={page}
            totalPages={totalPages}
            totalCount={totalCount}
            firstItem={firstItem}
            lastItem={lastItem}
            pageSize={pageSize}
            onPageSizeChange={setPageSize}
            onPageChange={setPage}
            visiblePages={visiblePages}
          />
        )}
      </div>
    </div>
  )
}