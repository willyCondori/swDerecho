// src/api/dashboardApi.js
import api from './axiosInstance'

const dashboardApi = {
  /**
   * GET /api/dashboard/resumen/ — panorama general del bufete.
   * Administrador/Abogado reciben el resumen completo (casos_por_usuario,
   * casos_por_mes, normas_mas_consultadas incluidos); Asistente recibe
   * solo los agregados de sus propios casos, con esas tres listas vacías.
   */
  resumen() {
    return api.get('/api/dashboard/resumen/')
  },
}

export default dashboardApi
