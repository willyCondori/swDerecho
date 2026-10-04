// modules/catalogo/hooks/useCargaArticulos.js
import { useCallback, useEffect, useRef, useState } from 'react'
import cargaArticulosApi from '../../../api/cargaArticulosApi'
import catalogoApi from '../../../api/catalogoApi'

import useAuthStore from '../../auth/store/authStore'

const cargasRecordadas = new Map()
useAuthStore.subscribe((actual, anterior) => {
  if (actual.user?.id !== anterior.user?.id) cargasRecordadas.clear()
})

const POLL_INTERVAL_MS = 1500
const POLL_OTRAS_MS = 3000

export function useCargaArticulos() {
  const usuario = useAuthStore((s) => s.user?.id)
  const [jerarquias, setJerarquias] = useState([])
  const [ramas,      setRamas]      = useState([])
  const [normas,     setNormas]     = useState([])
  const [loadingOpts, setLoadingOpts] = useState(true)

  const [taskId,    setTaskId]    = useState(null)
  const [estado,    setEstado]    = useState(null)
  const [progreso,  setProgreso]  = useState(0)
  const [paso,      setPaso]      = useState('')
  const [resumen,   setResumen]   = useState(null)
  const [error,     setError]     = useState(null)
  const [enviando,  setEnviando]  = useState(false)
  const [advertencias, setAdvertencias] = useState([])

  // Carga que ya estaba corriendo cuando el usuario volvió a entrar a la
  // pantalla (retomada), y cargas en curso de otros usuarios.
  const [cargaRetomada, setCargaRetomada] = useState(null)
  const [otrasCargas,   setOtrasCargas]   = useState([])
  const [verificandoCargas, setVerificandoCargas] = useState(true)

  const montado = useRef(false)
  const pollRef = useRef(null)
  const taskIdRef = useRef(null)

  useEffect(() => {
    const load = async () => {
      setLoadingOpts(true)
      try {
        const [jerarquiasRes, ramasRes, normasRes] = await Promise.all([
          catalogoApi.jerarquias(),
          catalogoApi.ramas(),
          catalogoApi.normas(),
        ])
        setJerarquias(jerarquiasRes.data ?? [])
        setRamas(ramasRes.data ?? [])
        setNormas(normasRes.data ?? [])
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

    if (!montado.current) return
    let consultando = false
    pollRef.current = setInterval(async () => {
      if (consultando) return
      consultando = true
      try {
        const { data } = await cargaArticulosApi.estado(id)
        if (!montado.current || taskIdRef.current !== id) return
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
        if (!montado.current || taskIdRef.current !== id) return
        setError('Se perdió la conexión con el servidor durante el seguimiento.')
        clearInterval(pollRef.current)
      } finally { consultando = false }
    }, POLL_INTERVAL_MS)
  }, [])

  useEffect(() => {
    montado.current = true
    return () => {
      montado.current = false
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  // Al entrar a la pantalla: si el usuario dejó una carga corriendo y salió,
  // el backend la sigue procesando aunque aquí ya no hubiera rastro. Se
  // consulta qué cargas están en curso y se retoma la propia (con su
  // progreso y, al terminar, su resultado). Las de otros usuarios solo se
  // muestran como aviso. Si falla, la pantalla funciona igual que antes.
  useEffect(() => {
    let cancelado = false
    const retomar = async () => {
      try {
        const recordada = cargasRecordadas.get(usuario)
        if (recordada) {
          if (!recordada.task_id) {
            const { data: inicio } = await recordada.inicio
            if (cancelado) return
            recordada.task_id = inicio.task_id
          }
          taskIdRef.current = recordada.task_id
          setTaskId(recordada.task_id)
          setCargaRetomada(recordada)
          const { data: avance } = await cargaArticulosApi.estado(recordada.task_id)
          if (cancelado) return
          setEstado(avance.estado)
          setProgreso(avance.progreso ?? 0)
          setPaso(avance.paso || '')
          if (avance.estado === 'SUCCESS') { setResumen(avance.resumen); setProgreso(100) }
          else if (avance.estado === 'FAILURE') setError(avance.error || 'El procesamiento falló.')
          else pollEstado(recordada.task_id)
          return
        }
        const { data } = await cargaArticulosApi.activas()
        if (cancelado || taskIdRef.current) return  // ya se inició una carga en esta sesión
        const lista = Array.isArray(data) ? data : []
        const propia = lista.find((c) => c.es_mia)
        if (propia) {
          taskIdRef.current = propia.task_id
          setTaskId(propia.task_id)
          setCargaRetomada(propia)
          if (usuario != null) cargasRecordadas.set(usuario, propia)
          setEstado(propia.estado)
          setProgreso(propia.progreso ?? 0)
          setPaso(propia.paso || '')
          pollEstado(propia.task_id)
        }
        setOtrasCargas(lista.filter((c) => c !== propia))
      } catch (e) {
        if (cancelado) return
        setError('No se pudo verificar el procesamiento del PDF. Vuelve a entrar cuando se restablezca la conexión.')
        console.error('No se pudieron consultar las cargas en curso:', e)
      } finally {
        if (!cancelado) setVerificandoCargas(false)
      }
    }
    retomar()
    return () => { cancelado = true }
  }, [pollEstado, usuario])

  // Mientras haya cargas de otros en curso, se refresca su avance hasta que terminen.
  const hayOtras = otrasCargas.length > 0
  useEffect(() => {
    if (!hayOtras) return undefined
    const id = setInterval(async () => {
      try {
        const { data } = await cargaArticulosApi.activas()
        const lista = Array.isArray(data) ? data : []
        setOtrasCargas(lista.filter((c) => c.task_id !== taskIdRef.current))
      } catch (e) {
        console.error('No se pudo refrescar el avance de otras cargas:', e)
      }
    }, POLL_OTRAS_MS)
    return () => clearInterval(id)
  }, [hayOtras])

  const cargar = useCallback(async (payload) => {
    setEnviando(true)
    setError(null)
    setAdvertencias([])
    setResumen(null)
    setProgreso(0)
    setPaso('Enviando archivo...')
    setEstado('PENDING')

    try {
      const inicio = cargaArticulosApi.cargar(payload)
      if (usuario != null) cargasRecordadas.set(usuario, { inicio, nombre_documento: payload.nombreDocumento || payload.archivo?.name })
      const { data } = await inicio
      if (useAuthStore.getState().user?.id !== usuario) return { success: true }
      taskIdRef.current = data.task_id
      if (usuario != null) cargasRecordadas.set(usuario, { task_id: data.task_id, nombre_documento: payload.nombreDocumento || payload.archivo?.name })
      setTaskId(data.task_id)

      const avisos = []
      if (data.advertencia)            avisos.push(data.advertencia)
      if (data.advertencia_duplicado)  avisos.push(data.advertencia_duplicado)
      if (avisos.length) setAdvertencias(avisos)

      pollEstado(data.task_id)
      return { success: true }
    } catch (err) {
      cargasRecordadas.delete(usuario)
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
  }, [pollEstado, usuario])

  const reset = useCallback(() => {
    cargasRecordadas.delete(usuario)
    if (pollRef.current) clearInterval(pollRef.current)
    taskIdRef.current = null
    setTaskId(null)
    setCargaRetomada(null)
    setEstado(null)
    setProgreso(0)
    setPaso('')
    setResumen(null)
    setError(null)
    setAdvertencias([])
  }, [usuario])

  const procesando = estado === 'PENDING' || estado === 'STARTED'

  return {
    jerarquias, ramas, normas, loadingOpts,
    cargar, reset,
    enviando, procesando,
    taskId, estado, progreso, paso, resumen, error, advertencias,
    cargaRetomada, otrasCargas, verificandoCargas,
  }
}
