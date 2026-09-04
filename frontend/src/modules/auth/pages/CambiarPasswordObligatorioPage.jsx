// modules/auth/pages/CambiarPasswordObligatorioPage.jsx
import { useNavigate } from 'react-router-dom'
import authApi from '../../../api/authApi'
import useAuthStore from '../store/authStore'
import FormCambioPassword from '../components/FormCambioPassword'
import styles from './LoginPage.module.css'

// Se muestra obligatoriamente cuando el usuario inicia sesión por
// primera vez con la contraseña temporal que le llegó por correo al
// crearse su cuenta (Usuario.debe_cambiar_password = True).
// PrivateRoute redirige acá a cualquier ruta protegida mientras el
// flag siga activo; al cambiar la contraseña con éxito se apaga el
// flag en el backend y en el store, y recién ahí se libera /dashboard.
//
// Ya hay sesión (JWT) en este punto, así que el formulario compartido
// (FormCambioPassword) NO muestra el campo de contraseña actual — el
// backend confía en el token, no hace falta re-verificar nada acá.
// Comparar con ForgotPasswordPage, que usa el mismo componente pero
// con mostrarPasswordActual=true porque ahí todavía no hay sesión.
export default function CambiarPasswordObligatorioPage() {
  const navigate = useNavigate()
  const { logout, marcarPasswordCambiada, user } = useAuthStore()

  const handleSubmit = async (valores) => {
    // password_actual no se muestra en este formulario (ver
    // FormCambioPassword), pero igual viaja en `valores` como string
    // vacío porque el componente comparte el mismo estado interno
    // para los dos flujos. CambioPasswordSerializer.password_actual
    // es CharField sin allow_blank, así que un "" lo rechazaría con
    // "Este campo no puede estar en blanco" — se saca acá antes de
    // mandar el request.
    const { password_actual, ...resto } = valores
    await authApi.cambiarPassword(resto)
    marcarPasswordCambiada()
    navigate('/dashboard', { replace: true })
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

        <FormCambioPassword onSubmit={handleSubmit} />

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