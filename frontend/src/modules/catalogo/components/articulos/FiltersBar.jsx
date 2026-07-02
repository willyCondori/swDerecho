// modules/catalogo/components/articulos/FiltersBar.jsx
import styles from '../../pages/articulos/VerArticulos.module.css'

export default function FiltersBar({
  search, onSearchChange,
  ramaId, onRamaChange, ramas,
  normaId, onNormaChange, normas,
  hayFiltros, totalCount, onReset,
}) {
  return (
    <div className={styles.filtersBar}>
      <div className={styles.searchWrapper}>
        <i className={`ti ti-search ${styles.searchIcon}`} aria-hidden="true" />
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Buscar por número, título o contenido..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          aria-label="Buscar artículos"
        />
        {search && (
          <button
            className={styles.searchClear}
            onClick={() => onSearchChange('')}
            aria-label="Limpiar búsqueda"
          >
            <i className="ti ti-x" aria-hidden="true" />
          </button>
        )}
      </div>

      <div className={styles.filtersDivider} />

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
            {totalCount.toLocaleString('es-BO')} resultados
          </span>
          <button className={styles.resetBtn} onClick={onReset}>
            <i className="ti ti-x" aria-hidden="true" />
            Limpiar
          </button>
        </>
      )}
    </div>
  )
}