// modules/auth/pages/ForgotPasswordPage.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import authApi from '../../../api/authApi'
import FormCambioPassword from '../components/FormCambioPassword'
import styles from './LoginPage.module.css'

// Recuperación de contraseña en dos pasos, en la misma página:
//
//   Paso "email"    -> el usuario ingresa su correo. El backend genera
//                      una contraseña temporal nueva y se la manda por
//                      Gmail (mismo mecanismo que al crear un usuario,
//                      ver core.utils.passwords.generar_password_aleatoria
//                      y UsuarioCreateSerializer).
//   Paso "confirmar" -> se muestra el mismo formulario que
//                      CambiarPasswordObligatorioPage
//                      (FormCambioPassword), pero acá SÍ con el campo
//                      de contraseña actual: el usuario pega la que le
//                      llegó por correo, más su contraseña nueva dos
//                      veces. Como todavía no hay sesión, esa
//                      contraseña temporal es la prueba de identidad
//                      (el backend la valida con check_password, como
//                      un login).
//
// El backend responde con el mismo mensaje genérico en el paso 1
// exista o no el email, para no revelar qué correos están
// registrados — por eso acá también se pasa al paso 2 sin distinguir
// "encontrado" de "no encontrado".
export default function ForgotPasswordPage() {
  const navigate = useNavigate()

  const [paso, setPaso] = useState('email') // 'email' | 'confirmar'
  const [email, setEmail] = useState('')
  const [mensajeSolicitud, setMensajeSolicitud] = useState('')
  const [error, setError] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const [exito, setExito] = useState(false)

  const validarEmail = (valor) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(valor)

  const handleSubmitEmail = async (e) => {
    e.preventDefault()
    setError(null)

    const valor = email.trim()
    if (!valor) {
      setError('El correo es obligatorio.')
      return
    }
    if (!validarEmail(valor)) {
      setError('Ingresá un correo electrónico válido.')
      return
    }

    setEnviando(true)
    try {
      const { data } = await authApi.solicitarRecuperacion(valor.toLowerCase())
      setEmail(valor.toLowerCase())
      setMensajeSolicitud(
        data?.detail || 'Si el correo está registrado, te enviamos una contraseña temporal.'
      )
      setPaso('confirmar')
    } catch (err) {
      const data = err.response?.data
      const msg =
        (typeof data?.email?.[0] === 'string' && data.email[0]) ||
        data?.detail ||
        'No se pudo procesar la solicitud. Intentá de nuevo en unos minutos.'
      setError(msg)
    } finally {
      setEnviando(false)
    }
  }

  const handleSubmitConfirmar = async (valores) => {
    await authApi.confirmarRecuperacion({ email, ...valores })
    setExito(true)
    setTimeout(() => navigate('/login', { replace: true }), 2500)
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
            Recuperación de cuenta
          </div>
          <h1 className={styles.panelTitle}>
            ¿Olvidaste tu<br />
            <span>contraseña?</span>
          </h1>
          <p className={styles.panelDesc}>
            {paso === 'email'
              ? 'Ingresá el correo asociado a tu cuenta y te mandamos una contraseña temporal.'
              : 'Usá la contraseña temporal que te llegó por correo para elegir una nueva.'}
          </p>
        </div>
      </aside>

      <main className={styles.form}>
        <div className={styles.formHeader}>
          <div className={styles.logo}>
            <div className={styles.logoIcon}>⚖</div>
            <span className={styles.logoText}>JurisIA</span>
          </div>
          <h2 className={styles.formTitle}>
            {paso === 'email' ? 'Recuperar contraseña' : 'Ingresá tu contraseña temporal'}
          </h2>
          <p className={styles.formSubtitle}>
            {paso === 'email'
              ? 'Te enviaremos una contraseña temporal a tu correo.'
              : `Te la mandamos a ${email}.`}
          </p>
        </div>

        {exito ? (
          <div className={styles.successBox} role="status">
            <i className="ti ti-circle-check" aria-hidden="true" />
            Contraseña actualizada correctamente. Te llevamos al login...
          </div>
        ) : paso === 'email' ? (
          <form onSubmit={handleSubmitEmail} noValidate>
            {error && (
              <div className={styles.errorBox} role="alert">
                <i className="ti ti-alert-circle" aria-hidden="true" />
                {error}
              </div>
            )}

            <div className={styles.fieldGroup}>
              <div className={styles.field}>
                <label htmlFor="email" className={styles.label}>
                  Correo electrónico
                </label>
                <div className={styles.inputWrapper}>
                  <span className={styles.inputIcon}>
                    <i className="ti ti-mail" aria-hidden="true" />
                  </span>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    placeholder="nombre@correo.com"
                    value={email}
                    onChange={(e) => { setEmail(e.target.value); if (error) setError(null) }}
                    className={`${styles.input} ${error ? styles.inputError : ''}`}
                  />
                </div>
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
                  Enviando...
                </>
              ) : (
                <>
                  <i className="ti ti-send" aria-hidden="true" />
                  Enviar contraseña temporal
                </>
              )}
            </button>
          </form>
        ) : (
          <>
            <div className={styles.successBox} role="status">
              <i className="ti ti-mail-check" aria-hidden="true" />
              {mensajeSolicitud}
            </div>

            <FormCambioPassword
              mostrarPasswordActual
              labelPasswordActual="Contraseña enviada por correo"
              placeholderPasswordActual="Pegá acá la contraseña temporal"
              textoBoton="Restablecer contraseña"
              onSubmit={handleSubmitConfirmar}
            />

            <p className={styles.hint}>
              ¿No te llegó nada?{' '}
              <a
                href="#"
                onClick={(e) => { e.preventDefault(); setPaso('email'); setError(null) }}
              >
                Volver a pedirla
              </a>
            </p>
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