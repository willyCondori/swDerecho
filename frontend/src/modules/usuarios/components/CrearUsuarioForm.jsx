// modules/usuarios/components/CrearUsuarioForm.jsx
import RolSelectField from './RolSelectField'
import styles from '../pages/UsuarioForm.module.css'

export default function CrearUsuarioForm({ form, fieldErrors, enviando, onChange, onSubmit }) {
  return (
    <form onSubmit={onSubmit} noValidate>
      <div className={styles.card}>
        <h2 className={styles.cardTitle}>
          <i className={`ti ti-user-plus ${styles.cardTitleIcon}`} aria-hidden="true" />
          Datos de acceso
        </h2>

        <div className={styles.formGrid}>
          <div className={styles.field}>
            <label htmlFor="usuario" className={styles.label}>Nombre de usuario</label>
            <input
              id="usuario"
              name="usuario"
              type="text"
              className={styles.input}
              value={form.usuario}
              onChange={onChange}
              autoComplete="username"
              placeholder="ej. jperez"
            />
            {fieldErrors.usuario && (
              <span className={styles.fieldError}>
                <i className="ti ti-alert-circle" aria-hidden="true" />
                {fieldErrors.usuario}
              </span>
            )}
          </div>

          <RolSelectField
            value={form.rolId}
            onChange={onChange}
            error={fieldErrors.rolId}
          />

          <div className={styles.field}>
            <label htmlFor="password" className={styles.label}>Contraseña</label>
            <input
              id="password"
              name="password"
              type="password"
              className={styles.input}
              value={form.password}
              onChange={onChange}
              autoComplete="new-password"
            />
            {fieldErrors.password && (
              <span className={styles.fieldError}>
                <i className="ti ti-alert-circle" aria-hidden="true" />
                {fieldErrors.password}
              </span>
            )}
          </div>

          <div className={styles.field}>
            <label htmlFor="confirmarPassword" className={styles.label}>Confirmar contraseña</label>
            <input
              id="confirmarPassword"
              name="confirmarPassword"
              type="password"
              className={styles.input}
              value={form.confirmarPassword}
              onChange={onChange}
              autoComplete="new-password"
            />
            {fieldErrors.confirmarPassword && (
              <span className={styles.fieldError}>
                <i className="ti ti-alert-circle" aria-hidden="true" />
                {fieldErrors.confirmarPassword}
              </span>
            )}
          </div>
        </div>

        <div className={styles.checkboxRow}>
          <input
            id="estado"
            name="estado"
            type="checkbox"
            className={styles.checkbox}
            checked={form.estado}
            onChange={onChange}
          />
          <label htmlFor="estado" className={styles.checkboxLabel}>
            <strong>Usuario activo.</strong> Si desmarcas esta opción, la cuenta se
            crea deshabilitada y no podrá iniciar sesión hasta que un
            administrador la active.
          </label>
        </div>

        <div className={styles.submitRow}>
          <button type="submit" className={styles.btnPrimary} disabled={enviando}>
            {enviando ? (
              <>
                <span className={styles.spinner} aria-hidden="true" />
                Creando...
              </>
            ) : (
              <>
                <i className="ti ti-user-plus" aria-hidden="true" />
                Crear usuario
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  )
}