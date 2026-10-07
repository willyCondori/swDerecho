import shared from '../../styles/shared.module.css'

/** onChange receives the search text; callers own debouncing and filtering. */
export default function SearchField({ value, onChange, placeholder = 'Buscar...', label = placeholder, classes = shared, clearable = false, ...inputProps }) {
  return <div className={classes.searchBox}>
    <i className={`ti ti-search ${classes.searchIcon}`} aria-hidden="true" />
    <input {...inputProps} type="text" className={classes.searchInput} aria-label={label}
      placeholder={placeholder} value={value} onChange={(event) => onChange(event.target.value)} />
    {clearable && value && <button type="button" className={classes.searchClear}
      aria-label="Limpiar búsqueda" onClick={() => onChange('')}>
      <i className="ti ti-x" aria-hidden="true" />
    </button>}
  </div>
}
