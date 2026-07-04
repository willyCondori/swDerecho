// src/api/casosApi.js
// ⚠️ Ya existía y lo usa DashboardPage (casosApi.misCasos). Fusiona esto con
// cualquier método adicional que ya tuvieras antes de reemplazar el archivo.
import api from './axiosInstance'

const casosApi = {
  /** GET /api/casos/ — lista con filtros (rama_id, cliente_id, fecha_desde, fecha_hasta, tiene_pdf, search) */
  listar(params = {}) {
    return api.get('/api/casos/', { params })
  },

  /** GET /api/casos/mis_casos/ — usado por el dashboard */
  misCasos(params = {}) {
    return api.get('/api/casos/mis_casos/', { params })
  },

  obtener(id) {
    return api.get(`/api/casos/${id}/`)
  },

  crear(data, config = {}) {
    return api.post('/api/casos/', data, config)
  },

  actualizar(id, data) {
    return api.patch(`/api/casos/${id}/`, data)
  },

  eliminar(id) {
    return api.delete(`/api/casos/${id}/`)
  },

  subirPdf(id, formData) {
    return api.post(`/api/casos/${id}/subir_pdf/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  hechos(id) {
    return api.get(`/api/casos/${id}/hechos/`)
  },

  petitorios(id) {
    return api.get(`/api/casos/${id}/petitorios/`)
  },

  resultado(id) {
    return api.get(`/api/casos/${id}/resultado/`)
  },

  articulos(id) {
    return api.get(`/api/casos/${id}/articulos/`)
  },

  analizar(id) {
    return api.post(`/api/casos/${id}/analizar/`)
  },
}

export default casosApi