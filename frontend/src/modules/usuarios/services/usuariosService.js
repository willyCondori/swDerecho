// modules/usuarios/services/usuariosService.js
import axiosClient from '../../../api/axiosClient'

// NOTA: ajusta este import si tu instancia de axios vive en otra ruta
// (equivalente al catalogoApi usado en el módulo de catálogo).

const USUARIOS_BASE = '/usuarios/'
const ROLES_BASE = '/roles/'

const usuariosService = {
  /** GET /api/usuarios/ */
  listar(params = {}) {
    return axiosClient.get(USUARIOS_BASE, { params })
  },

  /** GET /api/usuarios/{id}/ */
  obtener(id) {
    return axiosClient.get(`${USUARIOS_BASE}${id}/`)
  },

  /** POST /api/usuarios/ — crea usuario + asigna rol */
  crear(datos) {
    return axiosClient.post(USUARIOS_BASE, datos)
  },

  /** PATCH /api/usuarios/{id}/ — actualizar rol/estado */
  actualizar(id, datos) {
    return axiosClient.patch(`${USUARIOS_BASE}${id}/`, datos)
  },

  /** DELETE /api/usuarios/{id}/ — soft-delete */
  eliminar(id) {
    return axiosClient.delete(`${USUARIOS_BASE}${id}/`)
  },

  /** GET /api/usuarios/{id}/activar/ */
  activar(id) {
    return axiosClient.get(`${USUARIOS_BASE}${id}/activar/`)
  },

  /** PATCH /api/usuarios/{id}/perfil/ */
  actualizarPerfil(id, datos) {
    return axiosClient.patch(`${USUARIOS_BASE}${id}/perfil/`, datos)
  },
}

export const rolesService = {
  /** GET /api/roles/lista/ — compacto, para selects */
  lista() {
    return axiosClient.get(`${ROLES_BASE}lista/`)
  },

  /** GET /api/roles/ — listado completo con búsqueda/orden */
  listar(params = {}) {
    return axiosClient.get(ROLES_BASE, { params })
  },
}

export default usuariosService