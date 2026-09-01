import api from './axiosInstance'

const auditoriaApi = {
  listar(params = {}) {
    return api.get('/api/auditoria/', { params })
  },

  obtener(id) {
    return api.get(`/api/auditoria/${id}/`)
  },

  acciones() {
    return api.get('/api/auditoria/acciones/')
  },

  resumen(params = {}) {
    return api.get('/api/auditoria/resumen/', { params })
  },

  porUsuario(usuarioId, params = {}) {
    return api.get('/api/auditoria/por_usuario/', {
      params: { usuario_id: usuarioId, ...params },
    })
  },

  porTabla(tabla, params = {}) {
    return api.get('/api/auditoria/por_tabla/', {
      params: { tabla, ...params },
    })
  },
}

export default auditoriaApi
