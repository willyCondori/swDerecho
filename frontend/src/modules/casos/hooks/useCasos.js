// modules/casos/hooks/useCasos.js
import { useCallback, useEffect, useState } from 'react'
import casosApi from '../../../api/casosApi'

const PAGE_SIZE = 12

const initialFiltros = {
  search: '',
  rama_id: '',
  cliente_id: '',
  fecha_desde: '',
  fecha_hasta: '',
  tiene_pdf: '',
}

export default function useCasos() {
  const [casos, setCasos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [count, setCount] = useState(0)
  const [filtros, setFiltrosState] = useState(initialFiltros)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { page, page_size: PAGE_SIZE }
      if (filtros.search) params.search = filtros.search
      if (filtros.rama_id) params.rama_id = filtros.rama_id
      if (filtros.cliente_id) params.cliente_id = filtros.cliente_id
      if (filtros.fecha_desde) params.fecha_desde = filtros.fecha_desde
      if (filtros.fecha_hasta) params.fecha_hasta = filtros.fecha_hasta
      if (filtros.tiene_pdf !== '') params.tiene_pdf = filtros.tiene_pdf

      const { data } = await casosApi.listar(params)
      if (Array.isArray(data)) {
        setCasos(data)
        setCount(data.length)
      } else {
        setCasos(data.results ?? [])
        setCount(data.count ?? data.results?.length ?? 0)
      }
    } catch (e) {
      console.error('Error cargando casos:', e, e?.response?.data)
      setError('No se pudieron cargar los casos.')
    } finally {
      setLoading(false)
    }
  }, [page, filtros])

  useEffect(() => {
    load()
  }, [load])

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE))

  const setFiltros = (nuevo) => {
    setPage(1)
    setFiltrosState((prev) => ({ ...prev, ...nuevo }))
  }

  const limpiarFiltros = () => {
    setPage(1)
    setFiltrosState(initialFiltros)
  }

  return {
    casos,
    loading,
    error,
    page,
    setPage,
    totalPages,
    count,
    filtros,
    setFiltros,
    limpiarFiltros,
    reload: load,
  }
}