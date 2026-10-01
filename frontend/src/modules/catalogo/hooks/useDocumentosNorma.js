// modules/catalogo/hooks/useDocumentosNorma.js
import { useCallback, useEffect, useState } from 'react'
import catalogoApi from '../../../api/catalogoApi'
import { descargarBlob } from '../../documentos/utils/descargas'

// PDF que se subieron para extraer artículos de una norma (ver
// CargaArticulosView, que crea el registro DocumentoNorma al guardar el
// archivo). Solo lectura desde acá: no hay "subir" — eso pasa por el
// formulario de Catálogo → Cargar artículos.
export default function useDocumentosNorma(normaId) {
  const [documentos, setDocumentos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [eliminandoId, setEliminandoId] = useState(null)
  const [descargandoId, setDescargandoId] = useState(null)

  const cargar = useCallback(async () => {
    if (!normaId) return
    setLoading(true)
    setError(null)
    try {
      const { data } = await catalogoApi.documentosPorNorma(normaId)
      setDocumentos(data)
    } catch (e) {
      console.error('Error cargando documentos de la norma:', e, e?.response?.data)
      setError('No se pudieron cargar los documentos de esta norma.')
    } finally {
      setLoading(false)
    }
  }, [normaId])

  useEffect(() => {
    cargar()
  }, [cargar])

  const descargarDocumento = async (documento) => {
    setDescargandoId(documento.id)
    setError(null)
    try {
      const { data } = await catalogoApi.descargarDocumentoNorma(documento.id)
      descargarBlob(data, documento.nombre_original)
    } catch (e) {
      console.error('Error descargando documento de norma:', e, e?.response?.data)
      setError('No se pudo descargar el documento.')
    } finally {
      setDescargandoId(null)
    }
  }

  const eliminarDocumento = async (id) => {
    setEliminandoId(id)
    setError(null)
    try {
      await catalogoApi.eliminarDocumentoNorma(id)
      setDocumentos((prev) => prev.filter((d) => d.id !== id))
      return { ok: true }
    } catch (e) {
      console.error('Error eliminando documento de norma:', e, e?.response?.data)
      const msg = e?.response?.data?.detail || 'No se pudo eliminar el documento.'
      setError(msg)
      return { ok: false, error: msg }
    } finally {
      setEliminandoId(null)
    }
  }

  return {
    documentos,
    loading,
    error,
    eliminandoId,
    descargandoId,
    descargarDocumento,
    eliminarDocumento,
    reload: cargar,
  }
}
