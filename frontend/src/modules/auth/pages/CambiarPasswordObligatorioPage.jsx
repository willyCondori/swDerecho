// modules/auth/pages/CambiarPasswordObligatorioPage.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import authApi from '../../../api/authApi'
import useAuthStore from '../store/authStore'
import styles from './LoginPage.module.css'

// Se muestra obligatoriamente cuando el usuario inicia sesión por
// primera vez con la contraseña temporal que le llegó por correo al
// crearse su cuenta (Usuario.debe_cambiar_password = True).
// PrivateRoute redirige acá a cualquier ruta protegida mientras el
// flag siga activo; al cambiar la contraseña con éxito se apaga el
// flag en el backend y en el store, y recién ahí se libera /dashboard.
export default function CambiarPasswordObligatorioPage() {
  const navigate = useNavigate()
  const { logout, marcarPasswordCambiada, user } = useAuthStore()

  const [form, setForm] = useState({
    password_nuevo: '',
    password_confirm: '',
  })
  const [showPass, setShowPass]       = useState(false)
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError]             = useState(null)
  const [enviando, setEnviando]       = useState(false)

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    if (fieldErrors[name]) setFieldErrors((prev) => ({ ...prev, [name]: null }))
    if (error) setError(null)
  }

  const validar = () => {
    const errs = {}
    if (!form.password_nuevo) {
      errs.password_nuevo = 'La nueva contraseña es obligatoria.'
    } else if (form.password_nuevo.length < 8) {
      errs.password_nuevo = 'Mínimo 8 caracteres.'
    }
    if (form.password_nuevo !== form.password_confirm) {
      errs.password_confirm = 'Las contraseñas no coinciden.'
    }
    return errs
  }

  const extraerMensajeError = (err) => {
    const data = err.response?.data
    if (!data) return 'No se pudo cambiar la contraseña.'
    if (typeof data.detail === 'string') return data.detail
    const primerCampo = Object.values(data)[0]
    if (Array.isArray(primerCampo)) return primerCampo[0]
    return 'No se pudo cambiar la contraseña.'
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errs = validar()
    if (Object.keys(errs).length) {
      setFieldErrors(errs)
      return
    }

    setEnviando(true)
    setError(null)

    try {
      await authApi.cambiarPassword(form)
      marcarPasswordCambiada()
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(extraerMensajeError(err))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className={styles.root}>
      <aside className={styles.panel} aria-hidden="true">
        <div className={styles.panelGrid} />
        <div className={styles.panelAccent} />
        <div className={styles.panelAccent2} />
        <div className={styles.panelContent}>
          <div className={styles.panelBadge}>
            <span className={styles.panelBadgeDot} />
            Primer inicio de sesión
          </div>
          <h1 className={styles.panelTitle}>
            Tu cuenta<br />
            <span>está casi lista</span>
          </h1>
          <p className={styles.panelDesc}>
            Por seguridad, antes de continuar tenés que reemplazar la
            contraseña temporal que te enviamos por correo por una que
            solo vos conozcas.
          </p>
        </div>
      </aside>

      <main className={styles.form}>
        <div className={styles.formHeader}>
          <div className={styles.logo}>
            <div className={styles.logoIcon}>⚖</div>
            <span className={styles.logoText}>JurisIA</span>
          </div>
          <h2 className={styles.formTitle}>Cambiá tu contraseña</h2>
          <p className={styles.formSubtitle}>
            {user?.usuario ? <>Hola <strong>{user.usuario}</strong>, </> : null}
            elegí una contraseña nueva para continuar.
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          {error && (
            <div className={styles.errorBox} role="alert">
              <i className="ti ti-alert-circle" aria-hidden="true" />
              {error}
            </div>
          )}

          <div className={styles.fieldGroup}>
            <div className={styles.field}>
              <label htmlFor="password_nuevo" className={styles.label}>
                Nueva contraseña
              </label>
              <div className={styles.inputWrapper}>
                <span className={styles.inputIcon}>
                  <i className="ti ti-lock" aria-hidden="true" />
                </span>
                <input
                  id="password_nuevo"
                  name="password_nuevo"
                  type={showPass ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="••••••••"
                  value={form.password_nuevo}
                  onChange={handleChange}
                  className={`${styles.input} ${fieldErrors.password_nuevo ? styles.inputError : ''}`}
                />
                <button
                  type="button"
                  className={styles.togglePassword}
                  onClick={() => setShowPass((v) => !v)}
                  aria-label={showPass ? 'Ocultar contraseñas' : 'Mostrar contraseñas'}
                >
                  <i className={`ti ${showPass ? 'ti-eye-off' : 'ti-eye'}`} aria-hidden="true" />
                </button>
              </div>
              {fieldErrors.password_nuevo && (
                <span className={styles.fieldError}>
                  <i className="ti ti-alert-circle" aria-hidden="true" />
                  {fieldErrors.password_nuevo}
                </span>
              )}
            </div>

            <div className={styles.field}>
              <label htmlFor="password_confirm" className={styles.label}>
                Confirmar nueva contraseña
              </label>
              <div className={styles.inputWrapper}>
                <span className={styles.inputIcon}>
                  <i className="ti ti-lock-check" aria-hidden="true" />
                </span>
                <input
                  id="password_confirm"
                  name="password_confirm"
                  type={showPass ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="••••••••"
                  value={form.password_confirm}
                  onChange={handleChange}
                  className={`${styles.input} ${fieldErrors.password_confirm ? styles.inputError : ''}`}
                />
              </div>
              {fieldErrors.password_confirm && (
                <span className={styles.fieldError}>
                  <i className="ti ti-alert-circle" aria-hidden="true" />
                  {fieldErrors.password_confirm}
                </span>
              )}
            </div>
          </div>

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={enviando}
            aria-busy={enviando}
          >
            {enviando ? (
              <>
                <span className={styles.spinner} aria-hidden="true" />
                Guardando...
              </>
            ) : (
              <>
                <i className="ti ti-shield-check" aria-hidden="true" />
                Cambiar contraseña y continuar
              </>
            )}
          </button>
        </form>

        <footer className={styles.formFooter}>
          ¿No sos vos?{' '}
          <a href="#" onClick={(e) => { e.preventDefault(); logout(); navigate('/login', { replace: true }) }}>
            Cerrar sesión
          </a>
        </footer>
      </main>
    </div>
  )
}