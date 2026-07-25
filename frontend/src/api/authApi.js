// api/authApi.js
import api from './axiosInstance'

const AUTH_BASE = '/api/usuarios/auth'

const authApi = {
  login: (credentials) =>
    api.post(`${AUTH_BASE}/login/`, credentials),

  logout: (refreshToken) =>
    api.post(`${AUTH_BASE}/logout/`, { refresh: refreshToken }),

  refresh: (refreshToken) =>
    api.post(`${AUTH_BASE}/refresh/`, { refresh: refreshToken }),

  cambiarPassword: (payload) =>
    api.post(`${AUTH_BASE}/cambiar-password/`, payload),

  me: () =>
    api.get(`${AUTH_BASE}/me/`),
}

export default authApi
