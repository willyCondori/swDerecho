// modules/catalogo/hooks/useGestionJerarquias.js
import { useCallback, useEffect, useState } from 'react'
import catalogoApi from '../../../api/catalogoApi'

// 'activas' | 'eliminadas'
export default function useGestionJerarquias() {
  const [jerarquias, setJerarquias] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [estadoFiltro, setEstadoFiltroState] = useState('activas')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await catalogoApi.listarJerarquiasCompleto({
        search: search || undefined,
        estado: estadoFiltro === 'activas',
        ordering: 'nivel',
      })
      setJerarquias(Array.isArray(data) ? data : data.results ?? [])
    } catch (e) {
      console.error('Error cargando jerarquías:', e, e?.response?.data)
      setError('No se pudieron cargar las jerarquías.')
    } finally {
      setLoading(false)
    }
  }, [search, estadoFiltro])

  useEffect(() => {
    load()
  }, [load])

  const setEstadoFiltro = (value) => setEstadoFiltroState(value)

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

  const activarJerarquia = async (id) => {
    await catalogoApi.activarJerarquia(id)
    await load()
  }

  return {
    jerarquias,
    loading,
    error,
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
