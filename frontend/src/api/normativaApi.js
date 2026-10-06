import api from './axiosInstance'
const BASE = '/api/catalogo'
const normativaApi = {
  documentos: (params = {}) => api.get(`${BASE}/gaceta-documentos/`, { params }),
  descargar: (id) => api.get(`${BASE}/gaceta-documentos/${id}/descargar/`, { responseType: 'blob' }),
  sincronizar: (datos) => api.post(`${BASE}/gaceta/sincronizar/`, datos),
  estado: (id) => api.get(`${BASE}/tareas-normativas/${id}/`),
  gruposAvisos: (params = {}) => api.get(`${BASE}/cambios-normativos/grupos/`, { params }),
  cambios: (params = {}) => api.get(`${BASE}/cambios-normativos/`, { params }),
  cambio: (id) => api.get(`${BASE}/cambios-normativos/${id}/`),
  prepararRestauracion: (id) => api.get(`${BASE}/cambios-normativos/${id}/preparar-restauracion/`),
  restaurarCambio: (id) => api.post(`${BASE}/cambios-normativos/${id}/restaurar/`, { confirmar: true }),
  revisarCambio: (id, datos) => api.post(`${BASE}/cambios-normativos/${id}/revisar/`, datos),
  historial: (params = {}) => api.get(`${BASE}/historial-articulos/`, { params }),
  versiones: (articulo) => api.get(`${BASE}/versiones-articulos/`, { params: { articulo } }),
}
export default normativaApi
