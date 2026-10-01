// modules/usuarios/hooks/useGestionRoles.js
import { useCallback, useEffect, useState } from 'react'
import usuariosApi from '../../../api/usuariosApi'
import usePagination from '../../../hooks/usePagination'

const PAGE_SIZE = 10

// 'activos' | 'eliminados'
export default function useGestionRoles() {
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearchState] = useState('')
  const { page, setPage, count, setCount, totalPages, pageSize, retrocederSiVacia } =
    usePagination(PAGE_SIZE)
  const [estadoFiltro, setEstadoFiltroState] = useState('activos')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        estado: estadoFiltro === 'activos',
        ordering: 'nombre',
      }
      const { data } = await usuariosApi.listarRolesCompleto(params)
      if (Array.isArray(data)) {
        setRoles(data)
        setCount(data.length)
      } else {
        setRoles(data.results ?? [])
        setCount(data.count ?? data.results?.length ?? 0)
      }
    } catch (e) {
      if (retrocederSiVacia(e)) return
      console.error('Error cargando roles:', e, e?.response?.data)
      setError('No se pudieron cargar los roles.')
    } finally {
      setLoading(false)
    }
  }, [page, search, estadoFiltro, setCount, retrocederSiVacia])

  useEffect(() => {
    load()
  }, [load])

  const setSearch = (value) => {
    setPage(1)
    setSearchState(value)
  }

  const setEstadoFiltro = (value) => {
    setPage(1)
    setEstadoFiltroState(value)
  }

  const crearRol = async (payload) => {
    const { data } = await usuariosApi.crearRol(payload)
    await load()
    return data
  }

  const actualizarRol = async (id, payload) => {
    const { data } = await usuariosApi.actualizarRol(id, payload)
    await load()
    return data
  }

  const eliminarRol = async (id) => {
    await usuariosApi.eliminarRol(id)
    await load()
  }

  const activarRol = async (id) => {
    await usuariosApi.activarRol(id)
    await load()
  }

  return {
    roles,
    loading,
    error,
    count,
    page,
    setPage,
    totalPages,
    pageSize,
    search,
    setSearch,
    estadoFiltro,
    setEstadoFiltro,
    reload: load,
    crearRol,
    actualizarRol,
    eliminarRol,
    activarRol,
  }
}
