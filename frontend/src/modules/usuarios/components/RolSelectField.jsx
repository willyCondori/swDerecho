// modules/usuarios/components/RolSelectField.jsx
import { useRoles } from '../hooks/useRoles'
import styles from '../pages/UsuarioForm.module.css'

export default function RolSelectField({ value, onChange, error, disabled }) {
  const { roles, loading, error: rolesError } = useRoles()

  return (
    <div className={styles.field}>
      <label htmlFor="rolId" className={styles.label}>Rol</label>
      <select
        id="rolId"
        name="rolId"
        className={styles.select}
        value={value}
        onChange={onChange}
        disabled={disabled || loading}
      >
        <option value="">{loading ? 'Cargando roles...' : 'Selecciona un rol...'}</option>
        {roles.map((rol) => (
          <option key={rol.id} value={rol.id}>{rol.nombre}</option>
        ))}
      </select>
      {(error || rolesError) && (
        <span className={styles.fieldError}>
          <i className="ti ti-alert-circle" aria-hidden="true" />
          {error || rolesError}
        </span>
      )}
    </div>
  )
}