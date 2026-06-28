// api/casosApi.js
import api from './axiosInstance'

const CASOS_BASE = '/api/casos'

const casosApi = {
  listar:      (params) => api.get(`${CASOS_BASE}/`, { params }),
  misCasos:    (params) => api.get(`${CASOS_BASE}/mis_casos/`, { params }),
  obtener:     (id)     => api.get(`${CASOS_BASE}/${id}/`),
  crear:       (data)   => api.post(`${CASOS_BASE}/`, data),
  actualizar:  (id, data) => api.patch(`${CASOS_BASE}/${id}/`, data),
  eliminar:    (id)     => api.delete(`${CASOS_BASE}/${id}/`),
  subirPdf:    (id, file) => {
    const fd = new FormData()
    fd.append('archivo_pdf', file)
    return api.post(`${CASOS_BASE}/${id}/subir_pdf/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  hechos:     (id) => api.get(`${CASOS_BASE}/${id}/hechos/`),
  petitorios: (id) => api.get(`${CASOS_BASE}/${id}/petitorios/`),
  resultado:  (id) => api.get(`${CASOS_BASE}/${id}/resultado/`),
  articulos:  (id) => api.get(`${CASOS_BASE}/${id}/articulos/`),
  analizar:   (id) => api.post(`${CASOS_BASE}/${id}/analizar/`),
}

export default casosApi
