import api from './axiosInstance'

const jurisprudenciaApi = {
  listar: (params, config = {}) => api.get('/api/ia/jurisprudencia/', { ...config, params }),
  obtener: (id, config = {}) => api.get(`/api/ia/jurisprudencia/${id}/`, config),
  resumen: (config = {}) => api.get('/api/ia/jurisprudencia/resumen/', config),
  buscarTSJ: (params, config = {}) => api.get('/api/ia/tsj/buscar/', { ...config, params, timeout: 60000 }),
  incorporar: (fuente_id) => api.post('/api/ia/tsj/incorporar/', { fuente_id }),
  estado: (taskId, config = {}) => api.get(`/api/ia/tsj/tareas/${taskId}/`, config),
}
export default jurisprudenciaApi
