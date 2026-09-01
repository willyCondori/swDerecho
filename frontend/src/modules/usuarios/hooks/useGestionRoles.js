// modules/usuarios/hooks/useGestionRoles.js
import { useCallback, useEffect, useState } from 'react'
import usuariosApi from '../../../api/usuariosApi'

// 'activos' | 'eliminados'
export default function useGestionRoles() {
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [count, setCount] = useState(0)
  const [estadoFiltro, setEstadoFiltroState] = useState('activos')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {
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
      console.error('Error cargando roles:', e, e?.response?.data)
      setError('No se pudieron cargar los roles.')
    } finally {
      setLoading(false)
    }
  }, [search, estadoFiltro])

  useEffect(() => {
    load()
  }, [load])

  const setEstadoFiltro = (value) => setEstadoFiltroState(value)

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
