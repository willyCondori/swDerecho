// modules/catalogo/hooks/useGestionJerarquias.js
import { useCallback, useEffect, useState } from 'react'
import catalogoApi from '../../../api/catalogoApi'
import usePagination from '../../../hooks/usePagination'

const PAGE_SIZE = 10

// 'activas' | 'eliminadas'
export default function useGestionJerarquias() {
  const [jerarquias, setJerarquias] = useState([])
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
      const { data } = await catalogoApi.listarJerarquiasCompleto({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        estado: estadoFiltro === 'activas',
        ordering: 'nivel',
      })
      if (Array.isArray(data)) {
        setJerarquias(data)
        setCount(data.length)
      } else {
        setJerarquias(data.results ?? [])
        setCount(data.count ?? data.results?.length ?? 0)
      }
    } catch (e) {
      if (retrocederSiVacia(e)) return
      console.error('Error cargando jerarquías:', e, e?.response?.data)
      setError('No se pudieron cargar las jerarquías.')
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

  // Intenta crear la jerarquía. Si el nivel elegido ya está ocupado por
  // otra jerarquía activa, el backend responde 409 con
  // { conflicto: true, nivel, existente: { id, nombre } } en vez de
  // lanzar un error de validación normal; ese caso se deja pasar tal
  // cual para que la pantalla decida si pide confirmación al usuario.
  const crearJerarquia = async (payload) => {
    const { data } = await catalogoApi.crearJerarquia(payload)
    await load()
    return data
  }

  const actualizarJerarquia = async (id, payload) => {
    const { data } = await catalogoApi.actualizarJerarquia(id, payload)
    await load()
    return data
  }

  const eliminarJerarquia = async (id) => {
    await catalogoApi.eliminarJerarquia(id)
    await load()
  }

  const activarJerarquia = async (id, payload = {}) => {
    await catalogoApi.activarJerarquia(id, payload)
    await load()
  }

  return {
    jerarquias,
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
    crearJerarquia,
    actualizarJerarquia,
    eliminarJerarquia,
    activarJerarquia,
  }
}
