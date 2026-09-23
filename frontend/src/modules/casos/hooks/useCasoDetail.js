// modules/casos/hooks/useCasoDetail.js
import { useCallback, useEffect, useState } from 'react'
import casosApi from '../../../api/casosApi'
import { mensajeErrorApi } from '../utils/etapas'

export default function useCasoDetail(id) {
  const [caso, setCaso] = useState(null)
  const [articulos, setArticulos] = useState([])
  const [seguimientos, setSeguimientos] = useState([])
  const [guardandoEtapa, setGuardandoEtapa] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [analizando, setAnalizando] = useState(false)
  const [subiendoPdf, setSubiendoPdf] = useState(false)
  const [eliminando, setEliminando] = useState(false)

  const cargar = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await casosApi.obtener(id)
      setCaso(data)

      // La línea de tiempo es secundaria: si falla no debe tumbar el detalle.
      try {
        const { data: historial } = await casosApi.seguimiento(id)
        setSeguimientos(historial)
      } catch {
        setSeguimientos([])
      }

      // Los artículos solo existen si ya hay resultado de análisis
      if (data.resultado) {
        try {
          const { data: arts } = await casosApi.articulos(id)
          setArticulos(arts)
        } catch {
          setArticulos([])
        }
      }
    } catch (e) {
      console.error('Error cargando caso:', e, e?.response?.data)
      setError('No se pudo cargar el caso.')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    cargar()
  }, [cargar])

  const analizar = async () => {
    setAnalizando(true)
    setError(null)
    try {
      await casosApi.analizar(id)
      return true
    } catch (e) {
      console.error('Error al encolar análisis:', e, e?.response?.data)
      setError('No se pudo iniciar el análisis del caso.')
      return false
    } finally {
      setAnalizando(false)
    }
  }

  const subirPdf = async (archivo) => {
    setSubiendoPdf(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('archivo_pdf', archivo)
      await casosApi.subirPdf(id, formData)
      await cargar()
      return true
    } catch (e) {
      console.error('Error subiendo PDF:', e, e?.response?.data)
<<<<<<< HEAD
      setError('No se pudo adjuntar el PDF.')
=======
      setError(mensajeErrorApi(e, 'No se pudo adjuntar el PDF.'))
>>>>>>> 643e3e225dba5ab29e1278da6bd213a00a3abb20
      return false
    } finally {
      setSubiendoPdf(false)
    }
  }

  // Registra un cambio de etapa (y/o una nota) y refresca el caso y su
  // historial sin volver a mostrar el loader de página completa, para
  // no perder la posición de scroll ni lo escrito en el formulario.
  // Devuelve { ok: true } o { ok: false, error: '<mensaje>' }.
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

  // Envía el caso a la papelera. Devuelve { ok: true } o { ok: false, error }.
  const eliminar = async () => {
    setEliminando(true)
    try {
      await casosApi.eliminar(id)
      return { ok: true }
    } catch (e) {
      console.error('Error eliminando caso:', e, e?.response?.data)
      return { ok: false, error: mensajeErrorApi(e, 'No se pudo eliminar el caso.') }
    } finally {
      setEliminando(false)
    }
  }

  return {
    caso,
    articulos,
    seguimientos,
    guardandoEtapa,
    cambiarEtapa,
    loading,
    error,
    analizando,
    subiendoPdf,
    eliminando,
    eliminar,
    analizar,
    subirPdf,
    reload: cargar,
  }
}