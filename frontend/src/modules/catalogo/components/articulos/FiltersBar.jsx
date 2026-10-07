import SearchField from '../../../../components/ui/SearchField'
// modules/catalogo/components/articulos/FiltersBar.jsx
import styles from '../../pages/articulos/VerArticulos.module.css'

export default function FiltersBar({
  search, onSearchChange,
  ramaId, onRamaChange, ramas,
  normaId, onNormaChange, normas,
  hayFiltros, totalCount, onReset,
  numeroArticulo, onNumeroChange, buscando,
}) {
  return (
    <div className={styles.filtersBar}>
      <SearchField classes={{ ...styles, searchBox: styles.searchWrapper }}
        value={search} onChange={onSearchChange} clearable label="Buscar artículos"
        placeholder="Buscar por número, título o contenido..." />

      <div className={styles.filtersDivider} />
      <input className={styles.filterSelect} value={numeroArticulo} onChange={(e) => onNumeroChange(e.target.value)}
        aria-label="Número de artículo" placeholder="Número exacto: 23 bis" />

      <select
        className={styles.filterSelect}
        value={ramaId}
        onChange={(e) => onRamaChange(e.target.value)}
        aria-label="Filtrar por rama"
      >
        <option value="">Todas las ramas</option>
        {ramas.map((r) => (
          <option key={r.id} value={r.id}>{r.nombre}</option>
        ))}
      </select>

      <select
        className={styles.filterSelect}
        value={normaId}
        onChange={(e) => onNormaChange(e.target.value)}
        aria-label="Filtrar por norma"
      >
        <option value="">Todas las normas</option>
        {normas.map((n) => (
          <option key={n.id} value={n.id}>
            {n.sigla ? `${n.sigla} — ${n.nombre}` : n.nombre}
          </option>
        ))}
      </select>

      {hayFiltros && (
        <>
          <div className={styles.filtersDivider} />
          <span className={styles.activeCount}>
            {buscando ? 'Buscando…' : `${totalCount.toLocaleString('es-BO')} resultados`}
          </span>
          <button className={styles.resetBtn} onClick={onReset}>
            <i className="ti ti-x" aria-hidden="true" />
            Limpiar filtros
          </button>
        </>
      )}
    </div>
  )
}
