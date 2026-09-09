// modules/catalogo/hooks/useGestionJerarquias.js
import { useCallback, useEffect, useState } from 'react'
import catalogoApi from '../../../api/catalogoApi'

export default function useGestionJerarquias() {
  const [jerarquias, setJerarquias] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await catalogoApi.listarJerarquiasCompleto({
        search: search || undefined,
        ordering: 'nivel',
      })
      setJerarquias(Array.isArray(data) ? data : data.results ?? [])
    } catch (e) {
      console.error('Error cargando jerarquías:', e, e?.response?.data)
      setError('No se pudieron cargar las jerarquías.')
    } finally {
      setLoading(false)
    }
  }, [search])

  useEffect(() => {
    load()
  }, [load])

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

  return {
    jerarquias,
    loading,
    error,
    search,
    setSearch,
    reload: load,
    crearJerarquia,
    actualizarJerarquia,
    eliminarJerarquia,
  }
}
