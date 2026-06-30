// modules/catalogo/hooks/useCargaArticulos.js
import { useCallback, useEffect, useRef, useState } from 'react'
import cargaArticulosApi from '../../../api/cargaArticulosApi'
import catalogoApi from '../../../api/catalogoApi'

const POLL_INTERVAL_MS = 1500

export function useCargaArticulos() {
  const [fuentes,   setFuentes]   = useState([])
  const [normas,    setNormas]    = useState([])
  const [ramas,     setRamas]     = useState([])
  const [loadingOpts, setLoadingOpts] = useState(true)

  const [taskId,    setTaskId]    = useState(null)
  const [estado,    setEstado]    = useState(null)
  const [progreso,  setProgreso]  = useState(0)
  const [paso,      setPaso]      = useState('')
  const [resumen,   setResumen]   = useState(null)
  const [error,     setError]     = useState(null)
  const [enviando,  setEnviando]  = useState(false)
  const [advertencias, setAdvertencias] = useState([])

  const pollRef = useRef(null)

  useEffect(() => {
    const load = async () => {
      setLoadingOpts(true)
      try {
        const [fuentesRes, normasRes, ramasRes] = await Promise.all([
          cargaArticulosApi.fuentes(),
          catalogoApi.normas(),
          catalogoApi.ramas(),
        ])
        setFuentes(fuentesRes.data.fuentes ?? [])
        setNormas(normasRes.data ?? [])
        setRamas(ramasRes.data ?? [])
      } catch (e) {
        setError('No se pudieron cargar las opciones del formulario.')
      } finally {
        setLoadingOpts(false)
      }
    }
    load()
  }, [])

  const pollEstado = useCallback((id) => {
    if (pollRef.current) clearInterval(pollRef.current)

    pollRef.current = setInterval(async () => {
      try {
        const { data } = await cargaArticulosApi.estado(id)
        setEstado(data.estado)
        if (data.progreso != null) setProgreso(data.progreso)
        if (data.paso)             setPaso(data.paso)

        if (data.estado === 'SUCCESS') {
          setResumen(data.resumen)
          setProgreso(100)
          clearInterval(pollRef.current)
        } else if (data.estado === 'FAILURE') {
          setError(data.error || 'El procesamiento falló.')
          clearInterval(pollRef.current)
        }
      } catch (e) {
        setError('Se perdió la conexión con el servidor durante el seguimiento.')
        clearInterval(pollRef.current)
      }
    }, POLL_INTERVAL_MS)
  }, [])

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const cargar = useCallback(async (payload) => {
    setEnviando(true)
    setError(null)
    setAdvertencias([])
    setResumen(null)
    setProgreso(0)
    setPaso('Enviando archivo...')
    setEstado('PENDING')

    try {
      const { data } = await cargaArticulosApi.cargar(payload)
      setTaskId(data.task_id)

      const avisos = []
      if (data.advertencia)            avisos.push(data.advertencia)
      if (data.advertencia_duplicado)  avisos.push(data.advertencia_duplicado)
      if (avisos.length) setAdvertencias(avisos)

      pollEstado(data.task_id)
      return { success: true }
    } catch (err) {
      const errData = err.response?.data
      let msg = 'Error al subir el archivo.'
      if (errData) {
        if (typeof errData.detail === 'string') msg = errData.detail
        else {
          const firstKey = Object.keys(errData)[0]
          if (firstKey) {
            const val = errData[firstKey]
            msg = Array.isArray(val) ? val[0] : String(val)
          }
        }
      }
      setError(msg)
      setEstado(null)
      return { success: false, error: msg, fieldErrors: errData }
    } finally {
      setEnviando(false)
    }
  }, [pollEstado])

  const reset = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current)
    setTaskId(null)
    setEstado(null)
    setProgreso(0)
    setPaso('')
    setResumen(null)
    setError(null)
    setAdvertencias([])
  }, [])

  const procesando = estado === 'PENDING' || estado === 'STARTED'

  return {
    fuentes, normas, ramas, loadingOpts,
    cargar, reset,
    enviando, procesando,
    taskId, estado, progreso, paso, resumen, error, advertencias,
  }
}
