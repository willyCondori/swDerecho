// modules/catalogo/components/administrar/EntidadForm.jsx
import styles from '../../pages/AdministrarCatalogoPage.module.css'
import { sanearTextoLibre } from '../../../../utils/validators'

export default function EntidadForm({
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
        <i className={esEdicion ? 'ti ti-pencil' : 'ti ti-users'} aria-hidden="true" />
        {esEdicion ? 'Editar entidad jurídica' : 'Nueva entidad jurídica'}
      </h2>

      <div className={styles.formGrid}>
        <div className={`${styles.field} ${styles.fullWidth}`}>
          <label className={styles.label} htmlFor="entidadNombre">Nombre</label>
          <input
            id="entidadNombre"
            className={styles.input}
            name="nombre"
            value={form.nombre}
            onChange={(e) => onChange({ target: { name: 'nombre', value: sanearTextoLibre(e.target.value) } })}
            placeholder="Ej: Menor de edad, Funcionario público"
            disabled={enviando}
          />
          {fieldErrors.nombre && (
            <span className={styles.fieldError}>{fieldErrors.nombre}</span>
          )}
        </div>

        <div className={`${styles.field} ${styles.fullWidth}`}>
          <label className={styles.label} htmlFor="entidadDescripcion">Descripción (opcional)</label>
          <textarea
            id="entidadDescripcion"
            className={styles.textarea}
            name="descripcion"
            value={form.descripcion}
            onChange={(e) => onChange({ target: { name: 'descripcion', value: sanearTextoLibre(e.target.value) } })}
            placeholder="En qué casos aplica esta entidad y cómo afecta el análisis..."
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
          {enviando ? 'Guardando...' : esEdicion ? 'Guardar cambios' : 'Crear entidad'}
        </button>
      </div>
    </form>
  )
}
