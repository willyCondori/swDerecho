// modules/auth/pages/ResetPasswordPage.jsx
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import authApi from '../../../api/authApi'
import styles from './LoginPage.module.css'

// Paso 2 de la recuperación de contraseña: el usuario llega acá desde
// el enlace del correo (/recuperar-password/confirmar?token=...).
// Distinto de CambiarPasswordObligatorioPage: acá NO hay sesión
// todavía (por eso es AllowAny en el backend), así que el token de la
// URL es lo único que prueba que este pedido es legítimo.
export default function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''

  const [form, setForm] = useState({
    password_nuevo: '',
    password_confirm: '',
  })
  const [showPass, setShowPass]       = useState(false)
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError]             = useState(null)
  const [enviando, setEnviando]       = useState(false)
  const [exito, setExito]             = useState(false)

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
    if (!data) return 'No se pudo restablecer la contraseña.'
    if (typeof data.detail === 'string') return data.detail
    const primerCampo = Object.values(data)[0]
    if (Array.isArray(primerCampo)) return primerCampo[0]
    return 'No se pudo restablecer la contraseña.'
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!token) {
      setError('El enlace no es válido. Solicitá uno nuevo desde "¿Olvidaste tu contraseña?".')
      return
    }

    const errs = validar()
    if (Object.keys(errs).length) {
      setFieldErrors(errs)
      return
    }

    setEnviando(true)
    setError(null)

    try {
      await authApi.confirmarRecuperacion({ token, ...form })
      setExito(true)
      setTimeout(() => navigate('/login', { replace: true }), 2500)
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
            Nueva contraseña
          </div>
          <h1 className={styles.panelTitle}>
            Elegí una<br />
            <span>contraseña nueva</span>
          </h1>
          <p className={styles.panelDesc}>
            Este enlace es de un solo uso y vence a los 30 minutos de
            haberlo solicitado.
          </p>
        </div>
      </aside>

      <main className={styles.form}>
        <div className={styles.formHeader}>
          <div className={styles.logo}>
            <div className={styles.logoIcon}>⚖</div>
            <span className={styles.logoText}>JurisIA</span>
          </div>
          <h2 className={styles.formTitle}>Restablecer contraseña</h2>
          <p className={styles.formSubtitle}>
            Elegí una contraseña nueva para tu cuenta.
          </p>
        </div>

        {exito ? (
          <div className={styles.successBox} role="status">
            <i className="ti ti-circle-check" aria-hidden="true" />
            Contraseña actualizada correctamente. Te llevamos al login...
          </div>
        ) : (
          <>
            {!token && (
              <div className={styles.errorBox} role="alert">
                <i className="ti ti-alert-circle" aria-hidden="true" />
                Falta el token del enlace. Abrí el link del correo tal
                cual te llegó, o pedí uno nuevo.
              </div>
            )}

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
                disabled={enviando || !token}
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
                    Restablecer contraseña
                  </>
                )}
              </button>
            </form>
          </>
        )}

        <footer className={styles.formFooter}>
          <a href="/login" onClick={(e) => { e.preventDefault(); navigate('/login') }}>
            <i className="ti ti-arrow-left" aria-hidden="true" /> Volver a iniciar sesión
          </a>
        </footer>
      </main>
    </div>
  )
}
