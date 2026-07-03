// modules/usuarios/components/PerfilUsuarioForm.jsx
import styles from '../pages/UsuarioForm.module.css'

export default function PerfilUsuarioForm({
  form,
  fieldErrors,
  enviando,
  onChange,
  onSubmit,
}) {
  return (
    <form onSubmit={onSubmit} noValidate>
      <div className={styles.card}>
        <h2 className={styles.cardTitle}>
          <i className="ti ti-id-badge-2" />
          Información personal
        </h2>

        <div className={styles.formGrid}>
          <div className={styles.field}>
            <label className={styles.label}>Nombres</label>
            <input
              className={styles.input}
              name="nombres"
              value={form.nombres}
              onChange={onChange}
              placeholder="Nombres"
            />
            {fieldErrors.nombres && (
              <span className={styles.fieldError}>
                {fieldErrors.nombres}
              </span>
            )}
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Apellidos</label>
            <input
              className={styles.input}
              name="apellidos"
              value={form.apellidos}
              onChange={onChange}
              placeholder="Apellidos"
            />
            {fieldErrors.apellidos && (
              <span className={styles.fieldError}>
                {fieldErrors.apellidos}
              </span>
            )}
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Correo electrónico</label>
            <input
              className={styles.input}
              type="email"
              name="email"
              value={form.email}
              onChange={onChange}
              placeholder="correo@ejemplo.com"
            />
            {fieldErrors.email && (
              <span className={styles.fieldError}>
                {fieldErrors.email}
              </span>
            )}
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
                const valorFinal = soloNumeros.slice(0, 8)

                onChange({
                  target: {
                    name: 'telefono',
                    value: valorFinal,
                  },
                })
              }}
              placeholder="7########"
            />
            {fieldErrors.telefono && (
              <span className={styles.fieldError}>
                {fieldErrors.telefono}
              </span>
            )}
          </div>

          <div className={`${styles.field} ${styles.fullWidth}`}>
            <div className={styles.checkboxRow}>
              <input
                type="checkbox"
                className={styles.checkbox}
                name="estado"
                checked={form.estado}
                onChange={onChange}
              />
              <label className={styles.checkboxLabel}>
                Perfil activo
              </label>
            </div>
          </div>
        </div>

        <div className={styles.submitRow}>
          <button
            type="submit"
            className={styles.btnPrimary}
            disabled={enviando}
          >
            {enviando ? (
              <>
                <span className={styles.spinner} />
                Guardando...
              </>
            ) : (
              <>
                <i className="ti ti-device-floppy" />
                Guardar cambios
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  )
}