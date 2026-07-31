// src/api/clientesApi.js
import api from './axiosInstance'

const clientesApi = {
  listar(params = {}) {
    return api.get('/api/clientes', { params })
  },

  /** GET /api/clientes/clientes/lista/ — compacto para selects */
  listaCompacta() {
    return api.get('/api/clientes/lista/')
  },

  obtener(id) {
    return api.get(`/api/clientes/${id}/`)
  },

  crear(data) {
    return api.post('/api/clientes/', data)
  },

  actualizar(id, data) {
    return api.patch(`/api/clientes/${id}/`, data)
  },

  eliminar(id) {
    return api.delete(`/api/clientes/${id}/`)
  },

  casos(id, params = {}) {
    return api.get(`/api/clientes/${id}/casos/`, { params })
  },

  buscar(q) {
    return api.get('/api/clientes/buscar/', { params: { q } })
  },
}

export default clientesApi