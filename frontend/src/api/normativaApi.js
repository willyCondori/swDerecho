import api from './axiosInstance'
const BASE = '/api/catalogo'
const normativaApi = {
  documentos: (params = {}) => api.get(`${BASE}/gaceta-documentos/`, { params }),
  descargar: (id) => api.get(`${BASE}/gaceta-documentos/${id}/descargar/`, { responseType: 'blob' }),
  sincronizar: (datos) => api.post(`${BASE}/gaceta/sincronizar/`, datos),
  estado: (id) => api.get(`${BASE}/tareas-normativas/${id}/`),
  cambios: (params = {}) => api.get(`${BASE}/cambios-normativos/`, { params }),
  revisarCambio: (id, datos) => api.post(`${BASE}/cambios-normativos/${id}/revisar/`, datos),
  versiones: (articulo) => api.get(`${BASE}/versiones-articulos/`, { params: { articulo } }),
}
export default normativaApi
