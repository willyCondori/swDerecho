// App.jsx
import { useEffect, useRef } from 'react'
import { BrowserRouter } from 'react-router-dom'
import AppRouter from './routes/AppRouter'
import useAuthStore from './modules/auth/store/authStore'
import './styles/global.css'
import './styles/App.css'

// Tabler Icons CDN
const tablerLink = document.createElement('link')
tablerLink.rel  = 'stylesheet'
tablerLink.href = 'https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/dist/tabler-icons.min.css'
document.head.appendChild(tablerLink)

export default function App() {
  const bootstrap = useAuthStore((state) => state.bootstrap)

  // React StrictMode (activo en dev con Vite) monta cada componente dos
  // veces a propósito, disparando este efecto dos veces casi seguidas.
  // bootstrap() NO es idempotente: usa el refresh token de la cookie y,
  // con ROTATE_REFRESH_TOKENS activo, el backend lo invalida (blacklist)
  // en cuanto lo usa una vez. Si el efecto corre dos veces, la segunda
  // llamada intenta usar un refresh token que la primera ya quemó, y
  // el backend responde 401 → te patea a /login aunque la sesión sea
  // válida. Este ref evita que se dispare más de una vez por carga real
  // de la página.
  
  const yaInicio = useRef(false)

  useEffect(() => {
    if (yaInicio.current) return
    yaInicio.current = true
    bootstrap()
  }, [bootstrap])

  return (
    <BrowserRouter>
      <AppRouter />
    </BrowserRouter>
  )
}
