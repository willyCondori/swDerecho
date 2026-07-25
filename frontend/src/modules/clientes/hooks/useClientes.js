// modules/clientes/hooks/useClientes.js
import { useCallback, useEffect, useState } from 'react'
import clientesApi from '../../../api/clientesApi'

const PAGE_SIZE = 10

export default function useClientes() {
  const [clientes, setClientes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearchState] = useState('')
  const [page, setPage] = useState(1)
  const [count, setCount] = useState(0)

  const buscando = search.trim().length >= 2

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      if (buscando) {
        // /clientes/buscar/ no está paginado: descifra e itera en el backend
        const { data } = await clientesApi.buscar(search.trim())
        setClientes(data ?? [])
        setCount(data?.length ?? 0)
      } else {
        const { data } = await clientesApi.listar({ page, page_size: PAGE_SIZE })
        if (Array.isArray(data)) {
          setClientes(data)
          setCount(data.length)
        } else {
          setClientes(data.results ?? [])
          setCount(data.count ?? data.results?.length ?? 0)
        }
      }
    } catch (e) {
      console.error('Error cargando clientes:', e, e?.response?.data)
      setError('No se pudieron cargar los clientes.')
    } finally {
      setLoading(false)
    }
  }, [page, search, buscando])

  useEffect(() => {
    load()
  }, [load])

  const totalPages = buscando ? 1 : Math.max(1, Math.ceil(count / PAGE_SIZE))

  const setSearch = (value) => {
    setPage(1)
    setSearchState(value)
  }

  const eliminarCliente = async (id) => {
    await clientesApi.eliminar(id)
    await load()
  }

  return {
    clientes,
    loading,
    error,
    search,
    setSearch,
    buscando,
    page,
    setPage,
    totalPages,
    count,
    reload: load,
    eliminarCliente,
  }
}