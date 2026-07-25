import api from './axiosInstance'

const usuariosApi = {
  // ========= ROLES =========

  listarRoles() {
    return api.get('/api/usuarios/roles/lista/')
  },

  listarRolesCompleto(params = {}) {
    return api.get('/api/usuarios/roles/', { params })
  },

  crearRol(data) {
    return api.post('/api/usuarios/roles/', data)
  },

  actualizarRol(id, data) {
    return api.patch(`/api/usuarios/roles/${id}/`, data)
  },

  eliminarRol(id) {
    return api.delete(`/api/usuarios/roles/${id}/`)
  },

  // ========= USUARIOS =========

  listarUsuarios(params = {}) {
    return api.get('/api/usuarios/usuarios/', { params })
  },

  obtenerUsuario(id) {
    return api.get(`/api/usuarios/usuarios/${id}/`)
  },

  crearUsuario(data) {
    return api.post('/api/usuarios/usuarios/', data)
  },

  actualizarUsuario(id, data) {
    return api.patch(`/api/usuarios/usuarios/${id}/`, data)
  },

  eliminarUsuario(id) {
    return api.delete(`/api/usuarios/usuarios/${id}/`)
  },

  activarUsuario(id) {
    return api.get(`/api/usuarios/usuarios/${id}/activar/`)
  },

  actualizarPerfil(id, data) {
    return api.patch(`/api/usuarios/usuarios/${id}/perfil/`, data)
  },
}

export default usuariosApi