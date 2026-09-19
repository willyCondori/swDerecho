// modules/catalogo/hooks/useGestionNormas.js
import { useCallback, useEffect, useState } from 'react'
import catalogoApi from '../../../api/catalogoApi'
import usePagination from '../../../hooks/usePagination'

const PAGE_SIZE = 10
const SEARCH_DEBOUNCE_MS = 300

// estadoFiltro: 'activas' | 'eliminadas'
export default function useGestionNormas() {
  const [normas, setNormas] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearchState] = useState('')
  const [searchDebounced, setSearchDebounced] = useState('')
  const [estadoFiltro, setEstadoFiltroState] = useState('activas')
  const { page, setPage, count, setCount, totalPages, pageSize, retrocederSiVacia } =
    usePagination(PAGE_SIZE)

  // La búsqueda va al servidor; se espera un instante tras el último
  // tecleo para no disparar una petición por cada letra.
  useEffect(() => {
    const t = setTimeout(() => {
      setSearchDebounced(search.trim())
      setPage(1)
    }, SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(t)
  }, [search, setPage])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await catalogoApi.listarNormasCompleto({
        page,
        page_size: PAGE_SIZE,
        search: searchDebounced || undefined,
        estado: estadoFiltro === 'activas',
        ordering: 'nombre',
      })
      if (Array.isArray(data)) {
        setNormas(data)
        setCount(data.length)
      } else {
        setNormas(data.results ?? [])
        setCount(data.count ?? data.results?.length ?? 0)
      }
    } catch (e) {
      if (retrocederSiVacia(e)) return
      console.error('Error cargando normas:', e, e?.response?.data)
      setError('No se pudieron cargar las normas.')
    } finally {
      setLoading(false)
    }
  }, [page, searchDebounced, estadoFiltro, setCount, retrocederSiVacia])

  useEffect(() => {
    load()
  }, [load])

  const setEstadoFiltro = (value) => {
    setPage(1)
    setEstadoFiltroState(value)
  }

  const eliminarNorma = async (id) => {
    await catalogoApi.eliminarNorma(id)
    await load()
  }

  const activarNorma = async (id) => {
    await catalogoApi.activarNorma(id)
    await load()
  }

  return {
    normas,
    loading,
    error,
    search,
    setSearch: setSearchState,
    page,
    setPage,
    count,
    totalPages,
    pageSize,
    estadoFiltro,
    setEstadoFiltro,
    reload: load,
    eliminarNorma,
    activarNorma,
  }
}
