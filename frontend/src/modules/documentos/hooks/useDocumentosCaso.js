// modules/documentos/hooks/useDocumentosCaso.js
import { useCallback, useEffect, useState } from 'react'
import documentosApi from '../../../api/documentosApi'
import { mensajeErrorApi } from '../../casos/utils/etapas'
import { descargarBlob } from '../utils/descargas'

// Maneja el listado, subida, descarga y eliminación de los documentos
// de un caso (GET/POST/DELETE /api/documentos/), independiente del
// campo "PDF principal" que ya vive en el propio Caso.
export default function useDocumentosCaso(casoId) {
  const [documentos, setDocumentos] = useState([])
  const [tipos, setTipos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [subiendo, setSubiendo] = useState(false)
  const [eliminandoId, setEliminandoId] = useState(null)
  const [descargandoId, setDescargandoId] = useState(null)

  const cargar = useCallback(async () => {
    if (!casoId) return
    setLoading(true)
    setError(null)
    try {
      const { data } = await documentosApi.porCaso(casoId)
      setDocumentos(data)
    } catch (e) {
      console.error('Error cargando documentos del caso:', e, e?.response?.data)
      setError('No se pudieron cargar los documentos del caso.')
    } finally {
      setLoading(false)
    }
  }, [casoId])

  // El catálogo de tipos es secundario: si falla, igual se puede listar
  // y descargar documentos, solo no se podrá subir uno nuevo.
  const cargarTipos = useCallback(async () => {
    try {
      const { data } = await documentosApi.tipos()
      setTipos(data)
    } catch {
      setTipos([])
    }
  }, [])

  useEffect(() => {
    cargar()
    cargarTipos()
  }, [cargar, cargarTipos])

  const subirDocumento = async (archivo, tipoDocumentoId) => {
    setSubiendo(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('caso', casoId)
      formData.append('archivo', archivo)
      formData.append('tipo_documento', tipoDocumentoId)
      await documentosApi.subir(formData)
      await cargar()
      return { ok: true }
    } catch (e) {
      console.error('Error subiendo documento:', e, e?.response?.data)
      const msg = mensajeErrorApi(e, 'No se pudo subir el documento.')
      setError(msg)
      return { ok: false, error: msg }
    } finally {
      setSubiendo(false)
    }
  }

  const descargarDocumento = async (documento) => {
    setDescargandoId(documento.id)
    setError(null)
    try {
      const { data } = await documentosApi.descargar(documento.id)
      descargarBlob(data, documento.nombre_original)
    } catch (e) {
      console.error('Error descargando documento:', e, e?.response?.data)
      setError('No se pudo descargar el documento.')
    } finally {
      setDescargandoId(null)
    }
  }

  const eliminarDocumento = async (id) => {
    setEliminandoId(id)
    setError(null)
    try {
      await documentosApi.eliminar(id)
      setDocumentos((prev) => prev.filter((d) => d.id !== id))
      return { ok: true }
    } catch (e) {
      console.error('Error eliminando documento:', e, e?.response?.data)
      const msg = mensajeErrorApi(e, 'No se pudo eliminar el documento.')
      setError(msg)
      return { ok: false, error: msg }
    } finally {
      setEliminandoId(null)
    }
  }

  return {
    documentos,
    tipos,
    loading,
    error,
    subiendo,
    eliminandoId,
    descargandoId,
    subirDocumento,
    descargarDocumento,
    eliminarDocumento,
    reload: cargar,
  }
}
