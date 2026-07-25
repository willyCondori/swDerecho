// modules/catalogo/components/articulos/FormSelectField.jsx
import styles from '../../pages/articulos/CargaArticulosPage.module.css'

/**
 * Select genérico con label y mensaje de error, usado para
 * fuente, norma y rama en el formulario de carga.
 *
 * @param {{value: string|number, label: string}[]} options
 */
export default function FormSelectField({
  id,
  label,
  placeholder,
  value,
  onChange,
  options,
  disabled,
  error,
  fullWidth = false,
}) {
  return (
    <div className={`${styles.field} ${fullWidth ? styles.fullWidth : ''}`}>
      <label htmlFor={id} className={styles.label}>{label}</label>
      <select
        id={id}
        name={id}
        className={styles.select}
        value={value}
        onChange={onChange}
        disabled={disabled}
      >
        <option value="">{placeholder}</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      {error && (
        <span className={styles.fieldError}>
          <i className="ti ti-alert-circle" aria-hidden="true" />
          {error}
        </span>
      )}
    </div>
  )
}