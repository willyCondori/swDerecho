// modules/catalogo/hooks/useGestionRamas.js
import { useCallback, useEffect, useState } from 'react'
import catalogoApi from '../../../api/catalogoApi'
import usePagination from '../../../hooks/usePagination'

const PAGE_SIZE = 10

// 'activas' | 'eliminadas'
export default function useGestionRamas() {
  const [ramas, setRamas] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [estadoFiltro, setEstadoFiltroState] = useState('activas')
  const { page, setPage, count, setCount, totalPages, pageSize, retrocederSiVacia } =
    usePagination(PAGE_SIZE)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await catalogoApi.listarRamasCompleto({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        estado: estadoFiltro === 'activas',
        ordering: 'nombre',
      })
      if (Array.isArray(data)) {
        setRamas(data)
        setCount(data.length)
      } else {
        setRamas(data.results ?? [])
        setCount(data.count ?? data.results?.length ?? 0)
      }
    } catch (e) {
      if (retrocederSiVacia(e)) return
      console.error('Error cargando ramas de derecho:', e, e?.response?.data)
      setError('No se pudieron cargar las ramas de derecho.')
    } finally {
      setLoading(false)
    }
  }, [page, search, estadoFiltro, setCount, retrocederSiVacia])

  useEffect(() => {
    load()
  }, [load])

  const setEstadoFiltro = (value) => {
    setPage(1)
    setEstadoFiltroState(value)
  }

  const crearRama = async (payload) => {
    const { data } = await catalogoApi.crearRama(payload)
    await load()
    return data
  }

  const actualizarRama = async (id, payload) => {
    const { data } = await catalogoApi.actualizarRama(id, payload)
    await load()
    return data
  }

  const eliminarRama = async (id) => {
    await catalogoApi.eliminarRama(id)
    await load()
  }

  const activarRama = async (id) => {
    await catalogoApi.activarRama(id)
    await load()
  }

  return {
    ramas,
    loading,
    error,
    page,
    setPage,
    count,
    totalPages,
    pageSize,
    search,
    setSearch,
    estadoFiltro,
    setEstadoFiltro,
    reload: load,
    crearRama,
    actualizarRama,
    eliminarRama,
    activarRama,
  }
}
