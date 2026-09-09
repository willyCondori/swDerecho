// modules/catalogo/hooks/useGestionRamas.js
import { useCallback, useEffect, useState } from 'react'
import catalogoApi from '../../../api/catalogoApi'

// 'activas' | 'eliminadas'
export default function useGestionRamas() {
  const [ramas, setRamas] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [estadoFiltro, setEstadoFiltroState] = useState('activas')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await catalogoApi.listarRamasCompleto({
        search: search || undefined,
        estado: estadoFiltro === 'activas',
        ordering: 'nombre',
      })
      setRamas(Array.isArray(data) ? data : data.results ?? [])
    } catch (e) {
      console.error('Error cargando ramas de derecho:', e, e?.response?.data)
      setError('No se pudieron cargar las ramas de derecho.')
    } finally {
      setLoading(false)
    }
  }, [search, estadoFiltro])

  useEffect(() => {
    load()
  }, [load])

  const setEstadoFiltro = (value) => setEstadoFiltroState(value)

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
