// modules/usuarios/components/PerfilUsuarioForm.jsx
import styles from '../pages/UsuarioForm.module.css'

export default function PerfilUsuarioForm({ form, fieldErrors, enviando, onChange, onSubmit }) {
  return (
    <form onSubmit={onSubmit} noValidate>
      <div className={styles.card}>
        <h2 className={styles.cardTitle}>
          <i className={`ti ti-id-badge-2 ${styles.cardTitleIcon}`} aria-hidden="true" />
          Información personal
        </h2>

        <div className={styles.formGrid}>
          <div className={`${styles.field} ${styles.fullWidth}`}>
            <label htmlFor="nombreCompleto" className={styles.label}>Nombre completo</label>
            <input
              id="nombreCompleto"
              name="nombreCompleto"
              type="text"
              className={styles.input}
              value={form.nombreCompleto}
              onChange={onChange}
              placeholder="ej. Juana Pérez Rodríguez"
            />
            {fieldErrors.nombreCompleto && (
              <span className={styles.fieldError}>
                <i className="ti ti-alert-circle" aria-hidden="true" />
                {fieldErrors.nombreCompleto}
              </span>
            )}
          </div>

          <div className={styles.field}>
            <label htmlFor="email" className={styles.label}>Correo electrónico</label>
            <input
              id="email"
              name="email"
              type="email"
              className={styles.input}
              value={form.email}
              onChange={onChange}
              placeholder="correo@ejemplo.com"
            />
            {fieldErrors.email && (
              <span className={styles.fieldError}>
                <i className="ti ti-alert-circle" aria-hidden="true" />
                {fieldErrors.email}
              </span>
            )}
          </div>

          <div className={styles.field}>
            <label htmlFor="telefono" className={styles.label}>Teléfono</label>
            <input
              id="telefono"
              name="telefono"
              type="tel"
              className={styles.input}
              value={form.telefono}
              onChange={onChange}
              placeholder="ej. 70123456"
            />
          </div>

          <div className={`${styles.field} ${styles.fullWidth}`}>
            <label htmlFor="profesion" className={styles.label}>Profesión</label>
            <input
              id="profesion"
              name="profesion"
              type="text"
              className={styles.input}
              value={form.profesion}
              onChange={onChange}
              placeholder="ej. Abogado especialista en derecho civil"
            />
          </div>

          <div className={`${styles.field} ${styles.fullWidth}`}>
            <label htmlFor="biografia" className={styles.label}>Biografía</label>
            <textarea
              id="biografia"
              name="biografia"
              className={styles.textarea}
              value={form.biografia}
              onChange={onChange}
              rows={4}
              placeholder="Breve descripción profesional (opcional)"
            />
          </div>
        </div>

        <div className={styles.submitRow}>
          <button type="submit" className={styles.btnPrimary} disabled={enviando}>
            {enviando ? (
              <>
                <span className={styles.spinner} aria-hidden="true" />
                Guardando...
              </>
            ) : (
              <>
                <i className="ti ti-device-floppy" aria-hidden="true" />
                Guardar perfil
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  )
}