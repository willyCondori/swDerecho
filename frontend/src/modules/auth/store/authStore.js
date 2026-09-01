// modules/auth/store/authStore.js

import { create } from 'zustand'

import authApi from '../../../api/authApi'

import {
  getAccessToken,
  setAccessToken,
  clearAccessToken
} from '../../../api/tokenManager'

// Sin persist: nada de esto se guarda en localStorage.
// El access token vive en memoria (tokenManager) y el refresh token
// en una cookie httpOnly que este archivo ni siquiera puede leer.
//
// Al recargar la página, bootstrap() repone la sesión
// pidiendo un access token nuevo con esa cookie.

const useAuthStore = create((set, get) => ({

  user: null,

  isBootstrapping: true,

  isLoading: false,

  error: null,


  // ── Login ───────────────────────────────────────────────

  login: async (credentials) => {

    set({
      isLoading: true,
      error: null
    })

    try {

      const { data } = await authApi.login(credentials)

      console.log('========== LOGIN ==========')
      console.log('Respuesta completa del login:', data)
      console.log('Usuario recibido:', data.usuario)
      console.log('Rol completo recibido:', data.usuario?.rol)
      console.log('Nombre del rol:', data.usuario?.rol?.nombre)
      console.log('Tipo de rol:', typeof data.usuario?.rol)
      console.log('Tipo del nombre del rol:', typeof data.usuario?.rol?.nombre)
      console.log('============================')

      setAccessToken(data.access_token)

      set({
        user: data.usuario,
        isLoading: false,
        error: null,
      })

      return {
        success: true
      }

    } catch (err) {

      console.error('========== ERROR LOGIN ==========')
      console.error('Error completo:', err)
      console.error('Respuesta del servidor:', err.response?.data)
      console.error('==================================')

      const msg =
        err.response?.data?.non_field_errors?.[0] ||
        err.response?.data?.detail ||
        'Error al iniciar sesión'

      set({
        isLoading: false,
        error: msg
      })

      return {
        success: false,
        error: msg
      }
    }
  },


  // ── Logout ──────────────────────────────────────────────

  logout: async () => {

    try {

      await authApi.logout()

    } catch (_) {

      // silencioso

    } finally {

      clearAccessToken()

      set({
        user: null
      })

    }
  },


  // ── Restaurar sesión al cargar la app ───────────────────

  // Se llama una vez desde App.jsx.
  //
  // Usa la cookie httpOnly del refresh token para pedir
  // un access token nuevo.
  //
  // Si no existe una cookie válida, simplemente queda
  // deslogueado.

  bootstrap: async () => {

    try {

      console.log('========== BOOTSTRAP ==========')
      console.log('Intentando restaurar sesión...')

      const { data } = await authApi.refresh()

      console.log('Respuesta del refresh:', data)
      console.log(
        '¿Access token recibido?:',
        !!data.access_token
      )

      setAccessToken(data.access_token)

      const { data: me } = await authApi.me()

      console.log('========== /ME ==========')
      console.log('Usuario recibido:', me)
      console.log('Rol completo:', me?.rol)
      console.log('Nombre del rol:', me?.rol?.nombre)
      console.log('Tipo de rol:', typeof me?.rol)
      console.log(
        'Tipo del nombre del rol:',
        typeof me?.rol?.nombre
      )
      console.log('==========================')

      set({
        user: me,
        isBootstrapping: false
      })

    } catch (err) {

      console.error('========== ERROR BOOTSTRAP ==========')
      console.error('Error completo:', err)
      console.error('Respuesta:', err.response?.data)
      console.error('======================================')

      clearAccessToken()

      set({
        user: null,
        isBootstrapping: false
      })
    }
  },


  // ── Cargar usuario desde /me ─────────────────────────────

  fetchMe: async () => {

    set({
      isLoading: true
    })

    try {

      const { data } = await authApi.me()

      console.log('========== FETCH ME ==========')
      console.log('Usuario recibido:', data)
      console.log('Rol completo:', data?.rol)
      console.log('Nombre del rol:', data?.rol?.nombre)
      console.log('Tipo de rol:', typeof data?.rol)
      console.log(
        'Tipo del nombre del rol:',
        typeof data?.rol?.nombre
      )
      console.log('==============================')

      set({
        user: data,
        isLoading: false
      })

    } catch (err) {

      console.error('========== ERROR FETCH ME ==========')
      console.error('Error completo:', err)
      console.error('Respuesta:', err.response?.data)
      console.error('=====================================')

      set({
        isLoading: false
      })
    }
  },


  // ── Limpiar error ────────────────────────────────────────

  clearError: () => set({
    error: null
  }),


  // ── Helpers ─────────────────────────────────────────────


  isAuthenticated: () => !!getAccessToken(),


  // Normaliza el rol del usuario a un string en minúsculas, sin
  // importar si el backend lo mandó como objeto ({id, nombre}, la
  // forma normal desde /auth/me/ y /usuarios/) o como string suelto
  // (forma vieja que devolvía /auth/login/ antes de unificarla —
  // se deja este fallback por las dudas de que algún otro endpoint
  // vuelva a hacerlo). Todos los helpers de rol pasan por acá para
  // no repetir esta lógica en cada uno.
  _nombreRol: (user) => {
    const rol = user?.rol
    if (!rol) return ''
    const nombre = typeof rol === 'string' ? rol : rol.nombre
    return (nombre || '').toLowerCase()
  },


  // ── Verificar si el usuario es administrador ─────────────

  isAdmin: () => {

    const user = get().user
    const rol  = get()._nombreRol(user)

    console.log('========== isAdmin ==========')
    console.log('Usuario actual:', user)
    console.log('Rol completo:', user?.rol)
    console.log('Nombre del rol (normalizado):', rol)
    console.log('¿Es administrador?:', rol === 'administrador')
    console.log('==============================')

    return rol === 'administrador'
  },


  // ── Verificar si el usuario es asistente (rol de solo lectura) ──

  isAsistente: () => {
    return get()._nombreRol(get().user) === 'asistente'
  },


  // ── ¿Puede crear/editar/eliminar? (administrador o abogado) ──
  // Espeja al permiso backend EsOperativo: Asistente = solo lectura.

  puedeEscribir: () => {
    const rol = get()._nombreRol(get().user)
    return rol === 'administrador' || rol === 'abogado'
  },


  // ── Obtener nombre del rol ───────────────────────────────

  rol: () => {

    const rol = get()._nombreRol(get().user)

    console.log('========== rol() ==========')
    console.log('Rol completo:', get().user?.rol)
    console.log('Nombre del rol (normalizado):', rol)
    console.log('Tipo:', typeof rol)
    console.log('============================')

    return rol || ''
  },

}))

export default useAuthStore