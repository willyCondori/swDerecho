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


// ── Debug helpers ──────────────────────────────────────────
// Antes cada función tenía 5-8 líneas de console.log repetidas, y
// corrían igual en producción (llegaron a exponer el access_token
// completo en la consola del navegador). Ahora es una sola línea por
// función, agrupada y colapsable en devtools, y solo corre en
// desarrollo (import.meta.env.DEV) — Vite la elimina del bundle de
// producción por dead-code-elimination al ser una constante estática.

function debugLog(etiqueta, datos) {
  if (!import.meta.env.DEV) return
  console.groupCollapsed(`🔐 ${etiqueta}`)
  Object.entries(datos || {}).forEach(([clave, valor]) => console.log(`${clave}:`, valor))
  console.groupEnd()
}

function debugError(etiqueta, err) {
  if (!import.meta.env.DEV) return
  console.groupCollapsed(`🔐 ${etiqueta}`)
  console.error('Error completo:', err)
  console.error('Respuesta del servidor:', err?.response?.data)
  console.groupEnd()
}


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

      debugLog('LOGIN', {
        'Respuesta completa': data,
        'Usuario recibido'  : data.usuario,
        'Rol recibido'      : data.usuario?.rol,
      })

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

      debugError('ERROR LOGIN', err)

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

      const { data } = await authApi.refresh()

      debugLog('BOOTSTRAP: refresh', {
        '¿Access token recibido?': !!data.access_token,
      })

      setAccessToken(data.access_token)

      const { data: me } = await authApi.me()

      debugLog('BOOTSTRAP: /me', {
        'Usuario recibido': me,
        'Rol recibido'    : me?.rol,
      })

      set({
        user: me,
        isBootstrapping: false
      })

    } catch (err) {

      debugError('ERROR BOOTSTRAP', err)

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

      debugLog('FETCH ME', {
        'Usuario recibido': data,
        'Rol recibido'    : data?.rol,
      })

      set({
        user: data,
        isLoading: false
      })

    } catch (err) {

      debugError('ERROR FETCH ME', err)

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

    debugLog('isAdmin', {
      'Usuario actual'  : user,
      'Rol normalizado' : rol,
      '¿Es admin?'      : rol === 'administrador',
    })

    return rol === 'administrador'
  },


  // ── Verificar si el usuario es asistente (rol de solo lectura) ──

  isAsistente: () => {
    return get()._nombreRol(get().user) === 'asistente'
  },


  // ── Puede crear/editar/eliminar (administrador o abogado) ──
  // Espeja al permiso backend EsOperativo: Asistente = solo lectura.

  puedeEscribir: () => {
    const rol = get()._nombreRol(get().user)
    return rol === 'administrador' || rol === 'abogado'
  },


  // ── Obtener nombre del rol ───────────────────────────────

  rol: () => {
    return get()._nombreRol(get().user)
  },

}))

export default useAuthStore