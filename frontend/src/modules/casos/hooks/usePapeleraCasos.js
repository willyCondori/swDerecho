// modules/casos/hooks/usePapeleraCasos.js
import { useCallback, useEffect, useState } from 'react'
import casosApi from '../../../api/casosApi'
import { mensajeErrorApi } from '../utils/etapas'

const PAGE_SIZE = 12

export default function usePapeleraCasos() {
  const [casos, setCasos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [count, setCount] = useState(0)
  const [search, setSearchState] = useState('')
  const [restaurandoId, setRestaurandoId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { page, page_size: PAGE_SIZE }
      if (search) params.search = search
      const { data } = await casosApi.papelera(params)
      if (Array.isArray(data)) {
        setCasos(data)
        setCount(data.length)
      } else {
        setCasos(data.results ?? [])
        setCount(data.count ?? data.results?.length ?? 0)
      }
    } catch (e) {
      console.error('Error cargando la papelera:', e, e?.response?.data)
      setError('No se pudo cargar la papelera de casos.')
    } finally {
      setLoading(false)
    }
  }, [page, search])

  useEffect(() => {
    load()
  }, [load])

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE))

  const setSearch = (valor) => {
    setPage(1)
    setSearchState(valor)
  }

  // Restaura un caso y recarga la lista. Si era el único de la última
  // página, retrocede una página para no quedar en una página vacía.
  // Devuelve { ok: true } o { ok: false, error: '<mensaje>' }.
  const restaurar = async (id) => {
    setRestaurandoId(id)
    try {
      await casosApi.restaurar(id)
      if (casos.length === 1 && page > 1) setPage((p) => p - 1)
      else await load()
      return { ok: true }
    } catch (e) {
      console.error('Error restaurando caso:', e, e?.response?.data)
      return { ok: false, error: mensajeErrorApi(e, 'No se pudo restaurar el caso.') }
    } finally {
      setRestaurandoId(null)
    }
  }

  return {
    casos, loading, error,
    page, setPage, totalPages, count,
    search, setSearch,
    restaurar, restaurandoId,
    reload: load,
  }
}
