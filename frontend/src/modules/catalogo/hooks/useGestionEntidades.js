// modules/catalogo/hooks/useGestionEntidades.js
import { useCallback, useEffect, useState } from 'react'
import catalogoApi from '../../../api/catalogoApi'

// 'activas' | 'eliminadas'
export default function useGestionEntidades() {
  const [entidades, setEntidades] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [estadoFiltro, setEstadoFiltroState] = useState('activas')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await catalogoApi.listarEntidadesCompleto({
        search: search || undefined,
        estado: estadoFiltro === 'activas',
        ordering: 'nombre',
      })
      setEntidades(Array.isArray(data) ? data : data.results ?? [])
    } catch (e) {
      console.error('Error cargando entidades jurídicas:', e, e?.response?.data)
      setError('No se pudieron cargar las entidades jurídicas.')
    } finally {
      setLoading(false)
    }
  }, [search, estadoFiltro])

  useEffect(() => {
    load()
  }, [load])

  const setEstadoFiltro = (value) => setEstadoFiltroState(value)

  const crearEntidad = async (payload) => {
    const { data } = await catalogoApi.crearEntidad(payload)
    await load()
    return data
  }

  const actualizarEntidad = async (id, payload) => {
    const { data } = await catalogoApi.actualizarEntidad(id, payload)
    await load()
    return data
  }

  const eliminarEntidad = async (id) => {
    await catalogoApi.eliminarEntidad(id)
    await load()
  }

  const activarEntidad = async (id) => {
    await catalogoApi.activarEntidad(id)
    await load()
  }

  return {
    entidades,
    loading,
    error,
    search,
    setSearch,
    estadoFiltro,
    setEstadoFiltro,
    reload: load,
    crearEntidad,
    actualizarEntidad,
    eliminarEntidad,
    activarEntidad,
  }
}
