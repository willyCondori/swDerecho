// src/api/documentosApi.js
import api from './axiosInstance'

const documentosApi = {
  /** GET /api/documentos/documentos/por_caso/?caso_id=X — documentos de un caso */
  porCaso(casoId) {
    return api.get('/api/documentos/documentos/por_caso/', { params: { caso_id: casoId } })
  },

  /** POST /api/documentos/documentos/ — sube un documento (FormData: caso, archivo, tipo_documento) */
  subir(formData) {
    return api.post('/api/documentos/documentos/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  /**
   * GET /api/documentos/documentos/{id}/descargar/ — descarga autenticada del archivo.
   * responseType 'blob' porque el backend devuelve el binario, no JSON.
   */
  descargar(id) {
    return api.get(`/api/documentos/documentos/${id}/descargar/`, { responseType: 'blob' })
  },

  /** DELETE /api/documentos/documentos/{id}/ — elimina registro y archivo físico [admin] */
  eliminar(id) {
    return api.delete(`/api/documentos/documentos/${id}/`)
  },

  /** GET /api/documentos/tipo-doc/ — catálogo de tipos de documento */
  tipos() {
    return api.get('/api/documentos/tipo-doc/')
  },
}

export default documentosApi
