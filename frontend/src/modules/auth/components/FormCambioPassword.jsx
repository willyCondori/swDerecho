// modules/auth/components/FormCambioPassword.jsx
import { useState } from 'react'
import styles from '../pages/LoginPage.module.css'

// Formulario compartido por dos flujos:
//   1) CambiarPasswordObligatorioPage — cambio forzado del primer
//      login. Ya hay sesión (JWT), así que NO se pide password_actual:
//      el backend confía en el token, no hace falta re-verificar nada.
//   2) ForgotPasswordPage (paso 2) — confirmación de recuperación por
//      correo. Todavía NO hay sesión, así que sí se pide
//      password_actual: acá es la contraseña temporal que llegó por
//      Gmail, y funciona como prueba de identidad (el backend la
//      valida con check_password, igual que un login).
//
// mostrarPasswordActual decide si aparece ese primer campo. El resto
// (nueva contraseña + confirmar) es igual en los dos casos.
function extraerMensajeError(err) {
  const data = err.response?.data
  if (!data) return 'No se pudo procesar la solicitud.'
  if (typeof data.detail === 'string') return data.detail
  const primerCampo = Object.values(data)[0]
  if (Array.isArray(primerCampo)) return primerCampo[0]
  return 'No se pudo procesar la solicitud.'
}

export default function FormCambioPassword({
  mostrarPasswordActual = false,
  labelPasswordActual = 'Contraseña actual',
  placeholderPasswordActual = '••••••••',
  textoBoton = 'Cambiar contraseña y continuar',
  textoBotonEnviando = 'Guardando...',
  onSubmit, // async (valores: {password_actual?, password_nuevo, password_confirm}) => void
}) {
  const [form, setForm] = useState({
    password_actual: '',
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
    if (mostrarPasswordActual && !form.password_actual) {
      errs.password_actual = 'Este campo es obligatorio.'
    }
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
      await onSubmit(form)
    } catch (err) {
      setError(extraerMensajeError(err))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      {error && (
        <div className={styles.errorBox} role="alert">
          <i className="ti ti-alert-circle" aria-hidden="true" />
          {error}
        </div>
      )}

      <div className={styles.fieldGroup}>
        {mostrarPasswordActual && (
          <div className={styles.field}>
            <label htmlFor="password_actual" className={styles.label}>
              {labelPasswordActual}
            </label>
            <div className={styles.inputWrapper}>
              <span className={styles.inputIcon}>
                <i className="ti ti-mail" aria-hidden="true" />
              </span>
              <input
                id="password_actual"
                name="password_actual"
                type={showPass ? 'text' : 'password'}
                autoComplete="one-time-code"
                placeholder={placeholderPasswordActual}
                value={form.password_actual}
                onChange={handleChange}
                className={`${styles.input} ${fieldErrors.password_actual ? styles.inputError : ''}`}
              />
            </div>
            {fieldErrors.password_actual && (
              <span className={styles.fieldError}>
                <i className="ti ti-alert-circle" aria-hidden="true" />
                {fieldErrors.password_actual}
              </span>
            )}
          </div>
        )}

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
            {textoBotonEnviando}
          </>
        ) : (
          <>
            <i className="ti ti-shield-check" aria-hidden="true" />
            {textoBoton}
          </>
        )}
      </button>
    </form>
  )
}