// api/cargaArticulosApi.js
import api from './axiosInstance'

const BASE = '/api/catalogo/cargar-articulos'

const cargaArticulosApi = {
  fuentes: () => api.get(`${BASE}/fuentes/`),

  cargar: (payload) => {
    const fd = new FormData()
    fd.append('archivo', payload.archivo)
    fd.append('fuente', payload.fuente)
    fd.append('norma_id', payload.normaId)
    fd.append('rama_id', payload.ramaId)
    fd.append('sobrescribir', payload.sobrescribir ? 'true' : 'false')
    return api.post(`${BASE}/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  estado: (taskId) =>
    api.get(`${BASE}/estado/`, { params: { task_id: taskId } }),
}

export default cargaArticulosApi
