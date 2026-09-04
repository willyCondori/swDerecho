// api/authApi.js
import api from './axiosInstance'

const AUTH_BASE = '/api/usuarios/auth'

const authApi = {
  login: (credentials) =>
    api.post(`${AUTH_BASE}/login/`, credentials),

  logout: () =>
    api.post(`${AUTH_BASE}/logout/`),

  refresh: () =>
    api.post(`${AUTH_BASE}/refresh/`),

  cambiarPassword: (payload) =>
    api.post(`${AUTH_BASE}/cambiar-password/`, payload),

  me: () =>
    api.get(`${AUTH_BASE}/me/`),

  // Recuperación de contraseña por correo (sin sesión).
  solicitarRecuperacion: (email) =>
    api.post(`${AUTH_BASE}/recuperar-password/`, { email }),

  confirmarRecuperacion: (payload) =>
    api.post(`${AUTH_BASE}/recuperar-password/confirmar/`, payload),
}

export default authApi