// api/cargaArticulosApi.js
import api from './axiosInstance'

const BASE = '/api/catalogo/cargar-articulos'

function formulario(payload) {
  const fd = new FormData()
  fd.append('archivo', payload.archivo)
  if (payload.motorLectura) fd.append('motor_lectura', payload.motorLectura)
  if (payload.metadatos) fd.append('metadatos', JSON.stringify(payload.metadatos))
  if (payload.documentoOficialId) fd.append('documento_oficial_id', payload.documentoOficialId)
  if (payload.normaId) fd.append('norma_id', payload.normaId)
  else {
    fd.append('nombre_documento', payload.nombreDocumento)
    if (payload.sigla) fd.append('sigla', payload.sigla)
  }
  if (payload.jerarquiaId) fd.append('jerarquia_id', payload.jerarquiaId)
  fd.append('rama_id', payload.ramaId)
  if (payload.modoActualizacion) fd.append('modo_actualizacion', payload.modoActualizacion)
  if (payload.revisionToken) fd.append('revision_token', payload.revisionToken)
  if (payload.articulosSeleccionados) fd.append('articulos_seleccionados', JSON.stringify(payload.articulosSeleccionados))
  fd.append('sobrescribir', payload.sobrescribir ? 'true' : 'false')
  return fd
}

const cargaArticulosApi = {
  revisar: (payload) => api.post(`${BASE}/revisar/`, formulario(payload), {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  }),
  revisarConIA: async (payload, sigueVigente = () => true, onProgreso = () => {}) => {
    const inicio = await api.post(`${BASE}/revisar-iniciar/`, formulario(payload), {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    while (sigueVigente()) {
      await new Promise((resolve) => setTimeout(resolve, 1500))
      const { data } = await api.get(`/api/catalogo/tareas-normativas/${inicio.data.task_id}/`)
      if (!sigueVigente()) break
      onProgreso(data.resumen || {})
      if (data.estado === 'SUCCESS') return { data: data.resultado }
      if (data.estado === 'FAILURE') throw new Error(data.error || 'La lectura normativa falló.')
    }
    throw new Error('La revisión fue cancelada en esta pantalla.')
  },
  cargar: (payload) => {
    return api.post(`${BASE}/`, formulario(payload), {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  estado: (taskId) =>
    api.get(`${BASE}/estado/`, { params: { task_id: taskId } }),

  // Cargas que siguen corriendo en el servidor (de cualquier usuario), la
  // más reciente primero. Permite retomar la vista de progreso al volver.
  activas: () => api.get(`${BASE}/activas/`),
}

export default cargaArticulosApi
