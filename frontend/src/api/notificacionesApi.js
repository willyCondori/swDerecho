// src/api/notificacionesApi.js
import api from './axiosInstance'

const notificacionesApi = {
  listar(params = {}) {
    return api.get('/api/notificaciones/', { params })
  },
  noLeidasCount() {
    return api.get('/api/notificaciones/no_leidas_count/')
  },
  marcarLeida(id) {
    return api.post(`/api/notificaciones/${id}/marcar_leida/`)
  },
  marcarTodasLeidas() {
    return api.post('/api/notificaciones/marcar_todas_leidas/')
  },
}

export default notificacionesApi
