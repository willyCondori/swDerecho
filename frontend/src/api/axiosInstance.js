// api/axiosInstance.js
import axios from 'axios'
import { getAccessToken, setAccessToken, clearAccessToken } from './tokenManager'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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
    if (token) config.headers.Authorization = `Bearer ${token}`
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
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // Evita loop: si el propio /auth/refresh/ o /auth/login/ devuelven
    // 401, no hay que intentar refrescar de nuevo.
    const esRutaAuth =
      originalRequest?.url?.includes('/auth/refresh/') ||
      originalRequest?.url?.includes('/auth/login/')

    if (error.response?.status === 401 && !originalRequest._retry && !esRutaAuth) {
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

      originalRequest._retry = true
      isRefreshing = true

      try {
        // El refresh token viaja solo, como cookie httpOnly — no se lee
        // ni se manda nada desde JS.
        const { data } = await axios.post(
          `${BASE_URL}/api/usuarios/auth/refresh/`,
          {},
          { withCredentials: true },
        )
        const newAccess = data.access_token
        setAccessToken(newAccess)
        api.defaults.headers.common.Authorization = `Bearer ${newAccess}`
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
