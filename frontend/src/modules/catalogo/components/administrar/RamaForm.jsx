// modules/catalogo/components/administrar/RamaForm.jsx
import styles from '../../pages/AdministrarCatalogoPage.module.css'

export default function RamaForm({
  mode = 'crear', // 'crear' | 'editar'
  form,
  fieldErrors,
  enviando,
  onChange,
  onSubmit,
  onCancel,
}) {
  const esEdicion = mode === 'editar'

  return (
    <form onSubmit={onSubmit} noValidate className={styles.formCard}>
      <h2 className={styles.cardTitle}>
        <i className={esEdicion ? 'ti ti-pencil' : 'ti ti-gavel'} aria-hidden="true" />
        {esEdicion ? 'Editar rama de derecho' : 'Nueva rama de derecho'}
      </h2>

      <div className={styles.formGrid}>
        <div className={`${styles.field} ${styles.fullWidth}`}>
          <label className={styles.label} htmlFor="ramaNombre">Nombre</label>
          <input
            id="ramaNombre"
            className={styles.input}
            name="nombre"
            value={form.nombre}
            onChange={onChange}
            placeholder="Ej: Derecho Procesal Penal"
            disabled={enviando}
          />
          {fieldErrors.nombre && (
            <span className={styles.fieldError}>{fieldErrors.nombre}</span>
          )}
        </div>

        <div className={`${styles.field} ${styles.fullWidth}`}>
          <label className={styles.label} htmlFor="ramaDescripcion">Descripción (opcional)</label>
          <textarea
            id="ramaDescripcion"
            className={styles.textarea}
            name="descripcion"
            value={form.descripcion}
            onChange={onChange}
            placeholder="Qué tipo de casos y normas cubre esta rama..."
            disabled={enviando}
          />
          {fieldErrors.descripcion && (
            <span className={styles.fieldError}>{fieldErrors.descripcion}</span>
          )}
        </div>
      </div>

      {fieldErrors.detail && (
        <div className={styles.errorBanner}>{fieldErrors.detail}</div>
      )}

      <div className={styles.submitRow}>
        <button type="button" className={styles.btnSecondary} onClick={onCancel} disabled={enviando}>
          Cancelar
        </button>
        <button type="submit" className={styles.btnPrimary} disabled={enviando}>
          {enviando ? 'Guardando...' : esEdicion ? 'Guardar cambios' : 'Crear rama'}
        </button>
      </div>
    </form>
  )
}
