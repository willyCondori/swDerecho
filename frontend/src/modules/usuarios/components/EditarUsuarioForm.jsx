import RolSelectField from './RolSelectField'
import styles from '../pages/UsuarioForm.module.css'

export default function EditarUsuarioForm({
  usuario,
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
          <i className="ti ti-user" /> Datos de acceso
        </h2>

        <div className={styles.formGrid}>
          <div className={styles.field}>
            <label className={styles.label}>Usuario</label>
            <input className={styles.input} value={usuario?.usuario ?? form.usuario} disabled />
          </div>

          <div className={styles.field}>
            <RolSelectField className={styles.select} value={form.rolId} onChange={onChange} />
            {fieldErrors.rolId && (
              <span className={styles.fieldError}>{fieldErrors.rolId}</span>
            )}
          </div>
        </div>

        <div className={styles.checkboxRow} style={{ marginTop: 'var(--sp-3)' }}>
          <input
            type="checkbox"
            className={styles.checkbox}
            name="cambiarPassword"
            checked={form.cambiarPassword}
            onChange={onChange}
          />
          <label className={styles.checkboxLabel}>Cambiar contraseña</label>
        </div>

        {form.cambiarPassword && (
          <div className={styles.formGrid} style={{ marginTop: 'var(--sp-3)' }}>
            <div className={styles.field}>
              <label className={styles.label}>Nueva contraseña</label>
              <input
                className={styles.input}
                type="password"
                name="password"
                value={form.password}
                onChange={onChange}
              />
              {fieldErrors.password && (
                <span className={styles.fieldError}>{fieldErrors.password}</span>
              )}
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Confirmar contraseña</label>
              <input
                className={styles.input}
                type="password"
                name="confirmarPassword"
                value={form.confirmarPassword}
                onChange={onChange}
              />
              {fieldErrors.confirmarPassword && (
                <span className={styles.fieldError}>{fieldErrors.confirmarPassword}</span>
              )}
            </div>
          </div>
        )}

        <h2 className={styles.cardTitle} style={{ marginTop: 'var(--sp-4)' }}>Perfil</h2>

        <div className={styles.formGrid}>
          <div className={styles.field}>
            <label className={styles.label}>Nombres</label>
            <input className={styles.input} name="nombres" value={form.perfil.nombres} onChange={onChange} placeholder="Nombres" />
            {fieldErrors.nombres && (
              <span className={styles.fieldError}>{fieldErrors.nombres}</span>
            )}
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Apellidos</label>
            <input className={styles.input} name="apellidos" value={form.perfil.apellidos} onChange={onChange} placeholder="Apellidos" />
            {fieldErrors.apellidos && (
              <span className={styles.fieldError}>{fieldErrors.apellidos}</span>
            )}
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Email</label>
            <input className={styles.input} type="email" name="email" value={form.perfil.email} onChange={onChange} placeholder="ejemplo@correo.com" />
            {fieldErrors.email && (
              <span className={styles.fieldError}>{fieldErrors.email}</span>
            )}
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Teléfono</label>
            <input
              className={styles.input}
              type="text"
              name="telefono"
              value={form.perfil.telefono}
              onChange={(e) => {
                const soloNumeros = e.target.value.replace(/[^0-9]/g, '')
                const valorFinal = soloNumeros.slice(0, 8)
                onChange({ target: { name: 'telefono', value: valorFinal } })
              }}
              placeholder="7########"
            />
            {fieldErrors.telefono && <span className={styles.fieldError}>{fieldErrors.telefono}</span>}
          </div>
        </div>

        <div className={styles.checkboxRow} style={{ marginTop: 'var(--sp-4)' }}>
          <input type="checkbox" className={styles.checkbox} name="estado" checked={form.estado} onChange={onChange} />
          <label className={styles.checkboxLabel}>Usuario activo</label>
        </div>

        <div className={styles.submitRow}>
          <button type="submit" className={styles.btnPrimary} disabled={enviando}>
            {enviando ? 'Guardando...' : 'Guardar cambios'}
          </button>
        </div>
      </div>
    </form>
  )
}