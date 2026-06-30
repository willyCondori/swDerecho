// modules/auth/store/authStore.js
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import authApi from '../../../api/authApi'

const useAuthStore = create(
  persist(
    (set, get) => ({
      user:          null,
      accessToken:   null,
      refreshToken:  null,
      isLoading:     false,
      error:         null,

      // ── Login ───────────────────────────────────────────────
      login: async (credentials) => {
        set({ isLoading: true, error: null })
        try {
          const { data } = await authApi.login(credentials)
          localStorage.setItem('access_token',  data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          set({
            user:         data.usuario,
            accessToken:  data.access_token,
            refreshToken: data.refresh_token,
            isLoading:    false,
            error:        null,
          })
          return { success: true }
        } catch (err) {
          const msg =
            err.response?.data?.non_field_errors?.[0] ||
            err.response?.data?.detail ||
            'Error al iniciar sesión'
          set({ isLoading: false, error: msg })
          return { success: false, error: msg }
        }
      },

      // ── Logout ──────────────────────────────────────────────
      logout: async () => {
        const { refreshToken } = get()
        try {
          if (refreshToken) await authApi.logout(refreshToken)
        } catch (_) {
          // silencioso
        } finally {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          set({ user: null, accessToken: null, refreshToken: null })
        }
      },

      // ── Cargar usuario desde /me ─────────────────────────────
      fetchMe: async () => {
        set({ isLoading: true })
        try {
          const { data } = await authApi.me()
          set({ user: data, isLoading: false })
        } catch (_) {
          set({ isLoading: false })
        }
      },

      clearError: () => set({ error: null }),

      // ── Helpers ─────────────────────────────────────────────
      isAuthenticated: () => !!get().accessToken,
      isAdmin: () => get().user?.rol?.toLowerCase() === 'administrador',

      rol: () => get().user?.rol?.toLowerCase() || '',
    }),
    {
      name:    'auth-store',
      partialize: (state) => ({
        user:         state.user,
        accessToken:  state.accessToken,
        refreshToken: state.refreshToken,
      }),
    },
  ),
)

export default useAuthStore
