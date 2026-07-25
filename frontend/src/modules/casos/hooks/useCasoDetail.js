// modules/casos/hooks/useCasoDetail.js
import { useCallback, useEffect, useState } from 'react'
import casosApi from '../../../api/casosApi'

export default function useCasoDetail(id) {
  const [caso, setCaso] = useState(null)
  const [articulos, setArticulos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [analizando, setAnalizando] = useState(false)
  const [subiendoPdf, setSubiendoPdf] = useState(false)

  const cargar = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await casosApi.obtener(id)
      setCaso(data)

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
      setError('No se pudo adjuntar el PDF.')
      return false
    } finally {
      setSubiendoPdf(false)
    }
  }

  return {
    caso,
    articulos,
    loading,
    error,
    analizando,
    subiendoPdf,
    analizar,
    subirPdf,
    reload: cargar,
  }
}