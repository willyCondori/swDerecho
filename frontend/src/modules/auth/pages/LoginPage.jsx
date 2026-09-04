// modules/auth/pages/LoginPage.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import styles from './LoginPage.module.css'

export default function LoginPage() {
  const navigate  = useNavigate()
  const { login, isLoading, error, bloqueado, clearError } = useAuthStore()

  const [form, setForm]           = useState({ usuario: '', password: '' })
  const [showPass, setShowPass]   = useState(false)
  const [fieldErrors, setFieldErrors] = useState({})

  const validate = () => {
    const errs = {}
    if (!form.usuario.trim())   errs.usuario  = 'El usuario es obligatorio'
    if (!form.password)          errs.password = 'La contraseña es obligatoria'
    if (form.password && form.password.length < 8)
      errs.password = 'Mínimo 8 caracteres'
    return errs
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    if (fieldErrors[name]) setFieldErrors((prev) => ({ ...prev, [name]: null }))
    if (error) clearError()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    const errs = validate()
    if (Object.keys(errs).length) {
      setFieldErrors(errs)
      return
    }
    const result = await login(form)

    if (result.success) {
      const debeCambiar = useAuthStore.getState().debeCambiarPassword()
      navigate(debeCambiar ? '/cambiar-password' : '/dashboard')
    }
  }

  return (
    <div className={styles.root}>
      {/* ── Panel izquierdo decorativo ───────────────────── */}
      <aside className={styles.panel} aria-hidden="true">
        <div className={styles.panelGrid} />
        <div className={styles.panelAccent} />
        <div className={styles.panelAccent2} />
        <div className={styles.panelContent}>
          <div className={styles.panelBadge}>
            <span className={styles.panelBadgeDot} />
            Sistema activo · Bolivia
          </div>
          <h1 className={styles.panelTitle}>
            Análisis jurídico<br />
            <span>asistido por IA</span>
          </h1>
          <p className={styles.panelDesc}>
            Procesamiento semántico de casos legales bolivianos.
            Ranking automático de artículos aplicables.
          </p>
          <div className={styles.panelStats}>
            <div className={styles.statItem}>
              <span className={styles.statNum}>127</span>
              <span className={styles.statLabel}>Análisis IA</span>
            </div>
            <div className={styles.statItem}>
              <span className={styles.statNum}>0.87</span>
              <span className={styles.statLabel}>Precisión</span>
            </div>
            <div className={styles.statItem}>
              <span className={styles.statNum}>48</span>
              <span className={styles.statLabel}>Casos activos</span>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Formulario ──────────────────────────────────── */}
      <main className={styles.form}>
        <div className={styles.formHeader}>
          <div className={styles.logo}>
            <div className={styles.logoIcon}>⚖</div>
            <span className={styles.logoText}>JurisIA</span>
          </div>
          <h2 className={styles.formTitle}>Acceder al sistema</h2>
          <p className={styles.formSubtitle}>
            Ingresa tus credenciales para continuar
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          {/* Error global del servidor. Si vino con 423 Locked (ver
              authStore.login), es un bloqueo temporal por intentos
              fallidos: se muestra con candado y color ámbar en vez
              del rojo genérico de "credenciales incorrectas", para
              que se distinga de un simple error de tipeo. */}
          {error && bloqueado && (
            <div className={styles.lockBox} role="alert">
              <i className="ti ti-lock" aria-hidden="true" />
              {error}
            </div>
          )}
          {error && !bloqueado && (
            <div className={styles.errorBox} role="alert">
              <i className="ti ti-alert-circle" aria-hidden="true" />
              {error}
            </div>
          )}

          <div className={styles.fieldGroup}>
            {/* Usuario */}
            <div className={styles.field}>
              <label htmlFor="usuario" className={styles.label}>
                Usuario
              </label>
              <div className={styles.inputWrapper}>
                <span className={styles.inputIcon}>
                  <i className="ti ti-user" aria-hidden="true" />
                </span>
                <input
                  id="usuario"
                  name="usuario"
                  type="text"
                  autoComplete="username"
                  placeholder="nombre.usuario"
                  value={form.usuario}
                  onChange={handleChange}
                  className={`${styles.input} ${fieldErrors.usuario ? styles.inputError : ''}`}
                  aria-describedby={fieldErrors.usuario ? 'usuario-error' : undefined}
                  aria-invalid={!!fieldErrors.usuario}
                />
              </div>
              {fieldErrors.usuario && (
                <span id="usuario-error" className={styles.fieldError}>
                  <i className="ti ti-alert-circle" aria-hidden="true" />
                  {fieldErrors.usuario}
                </span>
              )}
            </div>

            {/* Contraseña */}
            <div className={styles.field}>
              <label htmlFor="password" className={styles.label}>
                Contraseña
              </label>
              <div className={styles.inputWrapper}>
                <span className={styles.inputIcon}>
                  <i className="ti ti-lock" aria-hidden="true" />
                </span>
                <input
                  id="password"
                  name="password"
                  type={showPass ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={form.password}
                  onChange={handleChange}
                  className={`${styles.input} ${fieldErrors.password ? styles.inputError : ''}`}
                  aria-describedby={fieldErrors.password ? 'password-error' : undefined}
                  aria-invalid={!!fieldErrors.password}
                />
                <button
                  type="button"
                  className={styles.togglePassword}
                  onClick={() => setShowPass((v) => !v)}
                  aria-label={showPass ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                >
                  <i className={`ti ${showPass ? 'ti-eye-off' : 'ti-eye'}`} aria-hidden="true" />
                </button>
              </div>
              {fieldErrors.password && (
                <span id="password-error" className={styles.fieldError}>
                  <i className="ti ti-alert-circle" aria-hidden="true" />
                  {fieldErrors.password}
                </span>
              )}
              <div className={styles.forgotPasswordRow}>
                <a
                  href="/recuperar-password"
                  className={styles.forgotPasswordLink}
                  onClick={(e) => { e.preventDefault(); navigate('/recuperar-password') }}
                >
                  ¿Olvidaste tu contraseña?
                </a>
              </div>
            </div>
          </div>

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={isLoading}
            aria-busy={isLoading}
          >
            {isLoading ? (
              <>
                <span className={styles.spinner} aria-hidden="true" />
                Verificando...
              </>
            ) : (
              <>
                <i className="ti ti-login" aria-hidden="true" />
                Iniciar sesión
              </>
            )}
          </button>
        </form>

        <footer className={styles.formFooter}>
          JurisIA · Sistema de análisis jurídico boliviano<br />
          Datos cifrados · ISO 27001
        </footer>
      </main>
    </div>
  )
}