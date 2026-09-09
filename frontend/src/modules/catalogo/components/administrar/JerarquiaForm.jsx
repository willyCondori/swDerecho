// modules/catalogo/components/administrar/JerarquiaForm.jsx
import styles from '../../pages/AdministrarCatalogoPage.module.css'

export default function JerarquiaForm({
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
        <i className={esEdicion ? 'ti ti-pencil' : 'ti ti-stack-2'} aria-hidden="true" />
        {esEdicion ? 'Editar jerarquía' : 'Nueva jerarquía normativa'}
      </h2>

      <div className={styles.formGrid}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="jerarquiaNombre">Nombre</label>
          <input
            id="jerarquiaNombre"
            className={styles.input}
            name="nombre"
            value={form.nombre}
            onChange={onChange}
            placeholder="Ej: Decreto Supremo"
            disabled={enviando}
          />
          {fieldErrors.nombre && (
            <span className={styles.fieldError}>{fieldErrors.nombre}</span>
          )}
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="jerarquiaNivel">Nivel</label>
          <input
            id="jerarquiaNivel"
            className={styles.input}
            name="nivel"
            type="number"
            min="1"
            value={form.nivel}
            onChange={onChange}
            placeholder="Ej: 5"
            disabled={enviando}
          />
          {fieldErrors.nivel && (
            <span className={styles.fieldError}>{fieldErrors.nivel}</span>
          )}
          <span className={styles.helpText}>
            Cuanto más bajo el número, mayor rango normativo (1 = Constitución).
          </span>
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
          {enviando ? 'Guardando...' : esEdicion ? 'Guardar cambios' : 'Crear jerarquía'}
        </button>
      </div>
    </form>
  )
}
