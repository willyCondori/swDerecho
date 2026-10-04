import { useCallback, useSyncExternalStore } from 'react'
import useAuthStore from '../../auth/store/authStore'
import cargaArticulosApi from '../../../api/cargaArticulosApi'

const VACIA = { revision: null, revisando: false, pasoRevision: '', errorRevision: '', documento: '' }
const sesiones = new Map()
const listeners = new Set()
const publicar = (id, estado) => {
  sesiones.set(id, estado)
  listeners.forEach((fn) => fn())
}
// El archivo y el resultado sobreviven a la navegación; no se guardan en localStorage.
useAuthStore.subscribe((actual, anterior) => {
  if (actual.user?.id !== anterior.user?.id) {
    sesiones.clear()
    listeners.forEach((fn) => fn())
  }
})

export function useRevisionPdf() {
  const usuario = useAuthStore((s) => s.user?.id)
  const estado = useSyncExternalStore(
    useCallback((fn) => { listeners.add(fn); return () => listeners.delete(fn) }, []),
    useCallback(() => sesiones.get(usuario) || VACIA, [usuario]),
  )
  const limpiarRevision = useCallback(() => {
    if (!sesiones.get(usuario)?.revisando) publicar(usuario, VACIA)
  }, [usuario])
  const revisarPdf = useCallback(async (payload) => {
    if (sesiones.get(usuario)?.revisando) return
    const trabajo = { ...VACIA, revisando: true, pasoRevision: 'Iniciando revisión del PDF…',
      documento: payload.nombreDocumento || payload.archivo.name }
    publicar(usuario, trabajo)
    let snapshot = trabajo
    const vigente = () => sesiones.get(usuario) === snapshot
    try {
      const { data } = await cargaArticulosApi.revisarAsincrono(payload, vigente, (avance) => {
          if (vigente() && avance.paso) {
            snapshot = { ...snapshot, pasoRevision: avance.paso }
            publicar(usuario, snapshot)
          }
        })
      if (vigente()) publicar(usuario, { ...snapshot, revisando: false, revision: { ...data, payload } })
    } catch (err) {
      if (!vigente()) return
      const datos = err.response?.data
      const mensaje = datos?.detail || (datos && Object.values(datos).flat()[0]) || err.message
      publicar(usuario, { ...snapshot, revisando: false,
        errorRevision: typeof mensaje === 'string' ? mensaje : 'No se pudo revisar el PDF.' })
    }
  }, [usuario])
  return { ...estado, revisarPdf, limpiarRevision }
}
