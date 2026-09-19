// modules/clientes/hooks/usePapeleraClientes.js
import { useCallback, useEffect, useState } from 'react'
import clientesApi from '../../../api/clientesApi'
import { mensajeErrorApi } from '../../casos/utils/etapas'

const PAGE_SIZE = 10

export default function usePapeleraClientes() {
  const [clientes, setClientes] = useState([])
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
      if (search.trim().length >= 2) params.search = search.trim()
      const { data } = await clientesApi.papelera(params)
      if (Array.isArray(data)) {
        setClientes(data)
        setCount(data.length)
      } else {
        setClientes(data.results ?? [])
        setCount(data.count ?? data.results?.length ?? 0)
      }
    } catch (e) {
      console.error('Error cargando la papelera de clientes:', e, e?.response?.data)
      setError('No se pudo cargar la papelera de clientes.')
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

  // Restaura un cliente (con los casos que se eliminaron junto con él) y
  // recarga la lista. Si era el único de la última página, retrocede una
  // página. Devuelve { ok: true, casosRestaurados } o { ok: false, error }.
  const restaurar = async (id) => {
    setRestaurandoId(id)
    try {
      const { data } = await clientesApi.restaurar(id)
      if (clientes.length === 1 && page > 1) setPage((p) => p - 1)
      else await load()
      return { ok: true, casosRestaurados: data?.casos_restaurados ?? 0 }
    } catch (e) {
      console.error('Error restaurando cliente:', e, e?.response?.data)
      return { ok: false, error: mensajeErrorApi(e, 'No se pudo restaurar el cliente.') }
    } finally {
      setRestaurandoId(null)
    }
  }

  return {
    clientes, loading, error,
    page, setPage, totalPages, count,
    search, setSearch,
    restaurar, restaurandoId,
    reload: load,
  }
}
