// modules/usuarios/components/RolForm.jsx
import styles from '../pages/RolesPage.module.css'

export default function RolForm({
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
        <i className={esEdicion ? 'ti ti-pencil' : 'ti ti-shield-plus'} aria-hidden="true" />
        {esEdicion ? 'Editar rol' : 'Nuevo rol'}
      </h2>

      <div className={styles.formGrid}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="rolNombre">Nombre</label>
          <input
            id="rolNombre"
            className={styles.input}
            name="nombre"
            value={form.nombre}
            onChange={onChange}
            placeholder="Ej: Recepcionista"
            disabled={enviando}
          />
          {fieldErrors.nombre && (
            <span className={styles.fieldError}>{fieldErrors.nombre}</span>
          )}
        </div>

        <div className={`${styles.field} ${styles.fullWidth}`}>
          <label className={styles.label} htmlFor="rolDescripcion">Descripción</label>
          <textarea
            id="rolDescripcion"
            className={styles.textarea}
            name="descripcion"
            value={form.descripcion}
            onChange={onChange}
            placeholder="Para qué se usa este rol y qué nivel de acceso otorga..."
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
        <button
          type="button"
          className={styles.btnSecondary}
          onClick={onCancel}
          disabled={enviando}
        >
          Cancelar
        </button>
        <button type="submit" className={styles.btnPrimary} disabled={enviando}>
          {enviando ? 'Guardando...' : esEdicion ? 'Guardar cambios' : 'Crear rol'}
        </button>
      </div>
    </form>
  )
}
