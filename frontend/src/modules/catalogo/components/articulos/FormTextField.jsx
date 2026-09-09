// modules/catalogo/components/articulos/FormTextField.jsx
import styles from '../../pages/articulos/CargaArticulosPage.module.css'

/**
 * Input de texto genérico con label y mensaje de error, usado para el
 * nombre del documento (ej. "Código de Procedimiento Penal") en el
 * formulario de carga. No es un <select>: cualquier nombre es válido, así
 * el catálogo puede crecer (CPP, Código de Comercio, un Decreto Supremo
 * puntual, etc.) sin tocar el código.
 */
export default function FormTextField({
  id,
  label,
  placeholder,
  value,
  onChange,
  disabled,
  error,
  helpText,
  fullWidth = false,
}) {
  return (
    <div className={`${styles.field} ${fullWidth ? styles.fullWidth : ''}`}>
      <label htmlFor={id} className={styles.label}>{label}</label>
      <input
        id={id}
        name={id}
        type="text"
        className={styles.select}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        disabled={disabled}
        autoComplete="off"
      />
      {helpText && !error && (
        <span className={styles.helpText}>{helpText}</span>
      )}
      {error && (
        <span className={styles.fieldError}>
          <i className="ti ti-alert-circle" aria-hidden="true" />
          {error}
        </span>
      )}
    </div>
  )
}
