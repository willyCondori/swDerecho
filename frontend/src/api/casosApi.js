// src/api/casosApi.js
// ⚠️ Ya existía y lo usa DashboardPage (casosApi.misCasos). Fusiona esto con
// cualquier método adicional que ya tuvieras antes de reemplazar el archivo.
import api from './axiosInstance'

const casosApi = {
  /** GET /api/casos/ — lista con filtros (rama_id, cliente_id, fecha_desde, fecha_hasta, tiene_pdf, etapa, search) */
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

  /** DELETE /api/casos/{id}/ — envía el caso a la papelera (se puede restaurar) */
  eliminar(id) {
    return api.delete(`/api/casos/${id}/`)
  },

  /** GET /api/casos/papelera/ — casos eliminados (admin y abogado). Params: page, page_size, search */
  papelera(params = {}) {
    return api.get('/api/casos/papelera/', { params })
  },

  /** POST /api/casos/{id}/restaurar/ — saca el caso de la papelera */
  restaurar(id) {
    return api.post(`/api/casos/${id}/restaurar/`)
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

  /** GET /api/casos/etapas/ — catálogo de etapas de seguimiento [{ value, label, orden }] */
  etapas() {
    return api.get('/api/casos/etapas/')
  },

  /** GET /api/casos/{id}/seguimiento/ — línea de tiempo del caso (más reciente primero) */
  seguimiento(id) {
    return api.get(`/api/casos/${id}/seguimiento/`)
  },

  /** POST /api/casos/{id}/cambiar_etapa/ — { etapa, nota? } [admin, abogado] */
  cambiarEtapa(id, data) {
    return api.post(`/api/casos/${id}/cambiar_etapa/`, data)
  },

  analizar(id) {
    return api.post(`/api/casos/${id}/analizar/`, null, {
      timeout: 300000,
    })
  },
}

export default casosApi