// modules/usuarios/pages/CrearUsuarioPage.jsx
import { useNavigate } from 'react-router-dom'
import { useCrearUsuario } from '../hooks/useCrearUsuario'
import UsuarioForm from '../components/UsuarioForm'
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
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)', marginBottom: 'var(--sp-2)' }}>
        <button
          type="button"
          onClick={() => navigate('/usuarios')}
          aria-label="Volver"
          style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '1.2rem' }}
        >
          <i className="ti ti-arrow-left" aria-hidden="true" />
        </button>
        <header className={styles.header} style={{ marginBottom: 0 }}>
          <h1 className={styles.title}>Crear nuevo usuario</h1>
          <p className={styles.subtitle}>
            Registra las credenciales de acceso y asigna el rol que
            definirá sus permisos dentro del sistema.
          </p>
        </header>
      </div>

      {!creado ? (
        <>
          <UsuarioForm
            mode="crear"
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