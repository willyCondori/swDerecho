import { useCallback, useEffect, useState } from 'react'
import catalogoApi from '../../../api/catalogoApi'
import { descargarBlob } from '../utils/descargas'

const PAGE_SIZE = 25

export default function useDocumentosNormativos() {
  const [filtros, setFiltros] = useState({ search: '', norma_id: '', rama_id: '', vigente: '' })
  const [page, setPage] = useState(1)
  const [revision, setRevision] = useState(0)
  const [lista, setLista] = useState({ results: [], count: 0 })
  const [catalogos, setCatalogos] = useState({ normas: [], ramas: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(null)
  const [catalogoError, setCatalogoError] = useState('')
  useEffect(() => {
    let activo = true
    Promise.all([catalogoApi.normas(), catalogoApi.ramas()]).then(([normas, ramas]) => {
      if (activo) setCatalogos({ normas: normas.data, ramas: ramas.data })
    }).catch(() => { if (activo) setCatalogoError('No se pudieron cargar las opciones de normas y ramas.') })
    return () => { activo = false }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    const timer = setTimeout(() => {
      const params = { page, page_size: PAGE_SIZE, ...filtros }
      catalogoApi.listarDocumentosNorma(params, controller.signal).then(({ data }) => {
        if (controller.signal.aborted) return
        const ultima = Math.max(1, Math.ceil(data.count / PAGE_SIZE))
        if (page > ultima) setPage(ultima)
        else setLista(data)
      }).catch((e) => {
        if (!controller.signal.aborted) setError(e?.response?.data?.detail || 'No se pudieron cargar los documentos normativos.')
      }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    }, 250)
    return () => { clearTimeout(timer); controller.abort() }
  }, [filtros, page, revision])

  const filtrar = (campo, valor) => {
    setFiltros((prev) => ({ ...prev, [campo]: valor }))
    setPage(1)
  }
  const limpiar = () => { setFiltros({ search: '', norma_id: '', rama_id: '', vigente: '' }); setPage(1) }
  const recargar = useCallback(() => setRevision((valor) => valor + 1), [])
  const ejecutar = async (documento, eliminar = false) => {
    setOcupado(documento.id)
    setError('')
    try {
      if (eliminar) {
        await catalogoApi.eliminarDocumentoNorma(documento.id)
        recargar()
      } else {
        const { data } = await catalogoApi.descargarDocumentoNorma(documento.id)
        descargarBlob(data, documento.nombre_original)
      }
    } catch (e) {
      setError(e?.response?.data?.detail || `No se pudo ${eliminar ? 'eliminar' : 'descargar'} el PDF.`)
    } finally { setOcupado(null) }
  }
  return { ...catalogos, ...lista, filtros, filtrar, limpiar, page, setPage, pageSize: PAGE_SIZE,
    loading, error, catalogoError, ocupado, ejecutar, recargar }
}
