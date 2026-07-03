// modules/usuarios/hooks/useUsuarios.js
import { useCallback, useEffect, useState } from 'react'
import usuariosApi from '../../../api/usuariosApi'

const PAGE_SIZE = 10

// 'activos' | 'eliminados' | 'todos'
export default function useUsuarios() {
  const [usuarios, setUsuarios] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [count, setCount] = useState(0)
  const [estadoFiltro, setEstadoFiltroState] = useState('activos')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
      }
      if (estadoFiltro === 'activos') params.estado = true
      if (estadoFiltro === 'eliminados') params.estado = false
      // 'todos' no manda el parámetro

      const { data } = await usuariosApi.listarUsuarios(params)
      if (Array.isArray(data)) {
        setUsuarios(data)
        setCount(data.length)
      } else {
        setUsuarios(data.results ?? [])
        setCount(data.count ?? data.results?.length ?? 0)
      }
    } catch (e) {
      console.error('Error cargando usuarios:', e, e?.response?.data)
      setError('No se pudieron cargar los usuarios.')
    } finally {
      setLoading(false)
    }
  }, [page, search, estadoFiltro])

  useEffect(() => {
    load()
  }, [load])

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE))

  const setEstadoFiltro = (value) => {
    setPage(1)
    setEstadoFiltroState(value)
  }

  const eliminarUsuario = async (id) => {
    await usuariosApi.eliminarUsuario(id)
    await load()
  }

  const recuperarUsuario = async (id) => {
    await usuariosApi.activarUsuario(id)
    await load()
  }

  return {
    usuarios,
    loading,
    error,
    search,
    setSearch: (value) => { setPage(1); setSearch(value) },
    page,
    setPage,
    totalPages,
    count,
    estadoFiltro,
    setEstadoFiltro,
    reload: load,
    eliminarUsuario,
    recuperarUsuario,
  }
}