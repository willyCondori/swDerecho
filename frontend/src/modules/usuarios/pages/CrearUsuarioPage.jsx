// modules/usuarios/pages/CrearUsuarioPage.jsx
import { useNavigate } from 'react-router-dom'
import { useCrearUsuario } from '../hooks/useCrearUsuario'
import CrearUsuarioForm from '../components/CrearUsuarioForm'
import styles from '../pages/UsuarioForm.module.css'

export default function CrearUsuarioPage() {
  const navigate = useNavigate()
  const {
    form, fieldErrors, enviando, error, creado,
    handleChange, submit, reset,
  } = useCrearUsuario()

  const handleSubmit = async (e) => {
    e.preventDefault()
    await submit()
  }

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <h1 className={styles.title}>Crear nuevo usuario</h1>
        <p className={styles.subtitle}>
          Registra las credenciales de acceso y asigna el rol que
          definirá sus permisos dentro del sistema.
        </p>
      </header>

      {!creado ? (
        <>
          <CrearUsuarioForm
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
        </>
      ) : (
        <div className={styles.resultCard}>
          <div className={styles.resultIcon}>
            <i className="ti ti-circle-check" aria-hidden="true" />
          </div>
          <div>
            <p className={styles.resultTitle}>Usuario creado correctamente</p>
            <p className={styles.resultSubtitle}>
              <strong>{creado.usuario}</strong> ya puede iniciar sesión con la
              contraseña asignada.
            </p>
          </div>
          <div className={styles.resultActions}>
            <button className={styles.btnSecondary} onClick={reset}>
              <i className="ti ti-plus" aria-hidden="true" />
              Crear otro usuario
            </button>
            <button
              className={styles.btnPrimary}
              onClick={() => navigate(`/usuarios`)}
            >
              <i className="ti ti-id-badge-2" aria-hidden="true" />
              ver otros registros
            </button>
          </div>
        </div>
      )}
    </div>
  )
}