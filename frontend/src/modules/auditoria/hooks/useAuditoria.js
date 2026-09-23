// modules/auditoria/hooks/useAuditoria.js
import { useCallback, useEffect, useState } from 'react'
import auditoriaApi from '../../../api/auditoriaApi'
import usePagination from '../../../hooks/usePagination'

const PAGE_SIZE = 25 // igual al PAGE_SIZE global de DRF (ver config/settings.py)

const FILTROS_INICIALES = {
  usuario: '',
  tabla: '',
  accion: '',
  fecha_desde: '',
  fecha_hasta: '',
}

export default function useAuditoria() {
  const [registros, setRegistros] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filtros, setFiltrosState] = useState(FILTROS_INICIALES)
  const [acciones, setAcciones] = useState([])
  const { page, setPage, count, setCount, totalPages, pageSize, retrocederSiVacia } =
    usePagination(PAGE_SIZE)

  useEffect(() => {
    auditoriaApi.acciones()
      .then(({ data }) => setAcciones(data ?? []))
      .catch(() => setAcciones([]))
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { page, page_size: PAGE_SIZE }
      if (filtros.usuario) params.usuario = filtros.usuario
      if (filtros.tabla) params.tabla = filtros.tabla
      if (filtros.accion) params.accion = filtros.accion
      if (filtros.fecha_desde) params.fecha_desde = filtros.fecha_desde
      if (filtros.fecha_hasta) params.fecha_hasta = filtros.fecha_hasta

      const { data } = await auditoriaApi.listar(params)
      if (Array.isArray(data)) {
        // Por si el backend alguna vez responde sin paginar.
        setRegistros(data)
        setCount(data.length)
      } else {
        setRegistros(data.results ?? [])
        setCount(data.count ?? data.results?.length ?? 0)
      }
    } catch (e) {
      if (retrocederSiVacia(e)) return
      console.error('Error cargando auditoría:', e, e?.response?.data)
      setError('No se pudo cargar el registro de auditoría.')
    } finally {
      setLoading(false)
    }
  }, [page, filtros, setCount, retrocederSiVacia])

  useEffect(() => {
    load()
  }, [load])

  const setFiltro = (campo, valor) => {
    setPage(1) // un filtro nuevo invalida la página en la que se estaba
    setFiltrosState((prev) => ({ ...prev, [campo]: valor }))
  }

  const limpiarFiltros = () => {
    setPage(1)
    setFiltrosState(FILTROS_INICIALES)
  }

  return {
    registros,
    loading,
    error,
    count,
    page,
    setPage,
    totalPages,
    pageSize,
    filtros,
    setFiltro,
    limpiarFiltros,
    acciones,
    reload: load,
  }
}
