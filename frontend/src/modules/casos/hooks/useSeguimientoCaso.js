// modules/casos/hooks/useSeguimientoCaso.js
// Versión liviana de useCasoDetail para la vista de seguimiento: solo pide
// lo que esa página necesita (encabezado del caso + línea de tiempo), sin
// los artículos del análisis ni las demás cosas del detalle completo.
import { useCallback, useEffect, useState } from 'react'
import casosApi from '../../../api/casosApi'
import { mensajeErrorApi } from '../utils/etapas'

export default function useSeguimientoCaso(id) {
  const [caso, setCaso] = useState(null)
  const [seguimientos, setSeguimientos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [guardandoEtapa, setGuardandoEtapa] = useState(false)

  const cargar = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [{ data: casoData }, { data: historial }] = await Promise.all([
        casosApi.obtener(id),
        casosApi.seguimiento(id),
      ])
      setCaso(casoData)
      setSeguimientos(historial)
    } catch (e) {
      console.error('Error cargando el seguimiento del caso:', e, e?.response?.data)
      setError('No se pudo cargar el seguimiento del caso.')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    cargar()
  }, [cargar])

  const cambiarEtapa = async (etapa, nota) => {
    setGuardandoEtapa(true)
    try {
      const payload = { etapa }
      if (nota) payload.nota = nota
      await casosApi.cambiarEtapa(id, payload)
      const [{ data: casoActualizado }, { data: historial }] = await Promise.all([
        casosApi.obtener(id),
        casosApi.seguimiento(id),
      ])
      setCaso(casoActualizado)
      setSeguimientos(historial)
      return { ok: true }
    } catch (e) {
      console.error('Error cambiando etapa:', e, e?.response?.data)
      return { ok: false, error: mensajeErrorApi(e, 'No se pudo registrar el seguimiento.') }
    } finally {
      setGuardandoEtapa(false)
    }
  }

  return { caso, seguimientos, loading, error, guardandoEtapa, cambiarEtapa, reload: cargar }
}
