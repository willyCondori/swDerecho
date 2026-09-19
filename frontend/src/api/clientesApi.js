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

  /**
   * DELETE /api/clientes/{id}/ — envía el cliente a la papelera (se puede restaurar).
   * Con casos activos responde 400 (code 'cliente_con_casos_activos'); con
   * eliminarCasos también envía sus casos a la papelera.
   */
  eliminar(id, { eliminarCasos = false } = {}) {
    return api.delete(`/api/clientes/${id}/`, {
      params: eliminarCasos ? { eliminar_casos: true } : undefined,
    })
  },

  /** GET /api/clientes/papelera/ — clientes eliminados (admin y abogado). Params: page, page_size, search */
  papelera(params = {}) {
    return api.get('/api/clientes/papelera/', { params })
  },

  /** POST /api/clientes/{id}/restaurar/ — restaura el cliente y los casos que se eliminaron con él */
  restaurar(id) {
    return api.post(`/api/clientes/${id}/restaurar/`)
  },

  casos(id, params = {}) {
    return api.get(`/api/clientes/${id}/casos/`, { params })
  },

  buscar(q) {
    return api.get('/api/clientes/buscar/', { params: { q } })
  },
}

export default clientesApi