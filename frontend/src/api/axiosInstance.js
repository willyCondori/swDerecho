// api/axiosInstance.js
import axios from 'axios'
import { getAccessToken, setAccessToken, clearAccessToken } from './tokenManager'
import { clearRequestCache } from './requestCache'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const esRutaPublicaAuth = (url = '') =>
  /\/auth\/(login|refresh|recuperar-password)(\/|$)/.test(url)

// Axios une baseURL y ruta sin convertir «/» + «/api» en el host «//api».
const refreshClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  withCredentials: true,
})

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
  // Necesario para que el navegador mande (y reciba) la cookie httpOnly
  // del refresh token en /auth/login, /auth/refresh y /auth/logout.
  withCredentials: true,
})

api.interceptors.request.use(
  (config) => {
    const token = getAccessToken()
    if (token && !esRutaPublicaAuth(config.url)) {
      config.headers.Authorization = `Bearer ${token}`
    } else {
      delete config.headers.Authorization
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ── Response: refrescar token si expira (401) ─────────────────────────
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error)
    else prom.resolve(token)
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => {
    if (!['get', 'head', 'options'].includes((response.config?.method || 'get').toLowerCase())) {
      clearRequestCache()
    }
    return response
  },
  async (error) => {
    const originalRequest = error.config

    // Evita loop: si el propio /auth/refresh/ o /auth/login/ devuelven
    // 401, no hay que intentar refrescar de nuevo.
    const esRutaAuth = esRutaPublicaAuth(originalRequest?.url)

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry && !esRutaAuth) {
      originalRequest._retry = true
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            return api(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      isRefreshing = true

      try {
        // El refresh token viaja solo, como cookie httpOnly — no se lee
        // ni se manda nada desde JS.
        const { data } = await refreshClient.post('/api/usuarios/auth/refresh/', {})
        const newAccess = data.access_token
        setAccessToken(newAccess)
        processQueue(null, newAccess)
        originalRequest.headers.Authorization = `Bearer ${newAccess}`
        return api(originalRequest)
      } catch (err) {
        processQueue(err, null)
        clearAccessToken()
        window.location.href = '/login'
        return Promise.reject(err)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)

export default api
