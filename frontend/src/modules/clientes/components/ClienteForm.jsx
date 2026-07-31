// modules/clientes/components/ClienteForm.jsx
import styles from '../pages/ClientesPage.module.css'

export default function ClienteForm({ form, fieldErrors, enviando, onChange, onSubmit, submitLabel = 'Crear cliente' }) {
  return (
    <form onSubmit={onSubmit} noValidate>
      <div className={styles.formCard}>
        <div className={styles.formGrid}>
          <div className={styles.field}>
            <label className={styles.label}>Nombres</label>
            <input className={styles.input} name="nombres" value={form.nombres} onChange={onChange} placeholder="Nombres" />
            {fieldErrors.nombres && <span className={styles.fieldError}>{fieldErrors.nombres}</span>}
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Apellidos</label>
            <input className={styles.input} name="apellidos" value={form.apellidos} onChange={onChange} placeholder="Apellidos" />
            {fieldErrors.apellidos && <span className={styles.fieldError}>{fieldErrors.apellidos}</span>}
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Teléfono</label>
            <input
              className={styles.input}
              type="text"
              name="telefono"
              value={form.telefono}
              onChange={(e) => {
                const soloNumeros = e.target.value.replace(/[^0-9]/g, '')
                onChange({ target: { name: 'telefono', value: soloNumeros.slice(0, 8) } })
              }}
              placeholder="7########"
            />
            {fieldErrors.telefono && <span className={styles.fieldError}>{fieldErrors.telefono}</span>}
          </div>
        </div>

        <div className={styles.submitRow}>
          <button type="submit" className={styles.btnPrimary} disabled={enviando}>
            {enviando ? 'Guardando...' : submitLabel}
          </button>
        </div>
      </div>
    </form>
  )
}