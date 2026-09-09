// modules/catalogo/hooks/useGestionRamas.js
import { useCallback, useEffect, useState } from 'react'
import catalogoApi from '../../../api/catalogoApi'

// El backend (RamaDerechoViewSet.get_queryset) solo devuelve ramas activas
// — no hay filtro por estado ni acción de reactivar para este catálogo —
// así que esta pantalla es de "crear + ver activas", sin la pestaña de
// "eliminadas" que sí tiene Roles.
export default function useGestionRamas() {
  const [ramas, setRamas] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await catalogoApi.listarRamasCompleto({
        search: search || undefined,
        ordering: 'nombre',
      })
      setRamas(Array.isArray(data) ? data : data.results ?? [])
    } catch (e) {
      console.error('Error cargando ramas de derecho:', e, e?.response?.data)
      setError('No se pudieron cargar las ramas de derecho.')
    } finally {
      setLoading(false)
    }
  }, [search])

  useEffect(() => {
    load()
  }, [load])

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

  return {
    ramas,
    loading,
    error,
    search,
    setSearch,
    reload: load,
    crearRama,
    actualizarRama,
    eliminarRama,
  }
}
