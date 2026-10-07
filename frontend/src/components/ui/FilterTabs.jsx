import shared from '../../styles/shared.module.css'

/** Toggle filters, rather than tab panels: each button exposes its pressed state. */
export default function FilterTabs({ options, value, onChange, label = 'Filtrar por estado', classes = shared }) {
  return <div className={classes.tabs} role="group" aria-label={label}>
    {options.map((option) => <button key={option.value} type="button"
      className={`${classes.tab} ${value === option.value ? classes.tabActive : ''}`}
      aria-pressed={value === option.value} disabled={option.disabled}
      onClick={() => onChange(option.value)}>{option.label}</button>)}
  </div>
}
