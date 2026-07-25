// modules/usuarios/pages/PerfilUsuarioPage.jsx
import { useParams } from 'react-router-dom'
import { usePerfilUsuario } from '../hooks/usePerfilUsuario'
import PerfilUsuarioForm from '../components/PerfilUsuarioForm'
import styles from '../pages/UsuarioForm.module.css'

// Ruta sugerida: /usuarios/:id/perfil

export default function PerfilUsuarioPage() {
  const { id } = useParams()
  const {
    form, fieldErrors, cargando, enviando, error, guardado,
    handleChange, submit,
  } = usePerfilUsuario(id)

  const handleSubmit = async (e) => {
    e.preventDefault()
    await submit()
  }

  if (cargando) {
    return (
      <div className={styles.root}>
        <p className={styles.loadingText}>Cargando perfil...</p>
      </div>
    )
  }

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <h1 className={styles.title}>Perfil de usuario</h1>
        <p className={styles.subtitle}>
          Completa los datos personales asociados a esta cuenta.
        </p>
      </header>

      <PerfilUsuarioForm
        form={form}
        fieldErrors={fieldErrors}
        enviando={enviando}
        onChange={handleChange}
        onSubmit={handleSubmit}
      />

      {error && (
        <div className={styles.errorBox}>
          <i className="ti ti-alert-triangle" aria-hidden="true" />
          <p>{error}</p>
        </div>
      )}

      {guardado && (
        <div className={styles.successBox}>
          <i className="ti ti-circle-check" aria-hidden="true" />
          <p>Perfil actualizado correctamente.</p>
        </div>
      )}
    </div>
  )
}