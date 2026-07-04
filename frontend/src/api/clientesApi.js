// src/api/clientesApi.js
import api from './axiosInstance'

const clientesApi = {
  /** GET /api/clientes/clientes/ — lista paginada */
  listar(params = {}) {
    return api.get('/api/clientes/clientes/', { params })
  },

  /** GET /api/clientes/clientes/lista/ — compacto para selects */
  listaCompacta() {
    return api.get('/api/clientes/clientes/lista/')
  },

  obtener(id) {
    return api.get(`/api/clientes/clientes/${id}/`)
  },

  crear(data) {
    return api.post('/api/clientes/clientes/', data)
  },

  actualizar(id, data) {
    return api.patch(`/api/clientes/clientes/${id}/`, data)
  },

  eliminar(id) {
    return api.delete(`/api/clientes/clientes/${id}/`)
  },

  casos(id, params = {}) {
    return api.get(`/api/clientes/clientes/${id}/casos/`, { params })
  },

  buscar(q) {
    return api.get('/api/clientes/clientes/buscar/', { params: { q } })
  },
}

export default clientesApi