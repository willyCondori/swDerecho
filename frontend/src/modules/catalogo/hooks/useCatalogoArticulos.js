import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import catalogoApi from '../../../api/catalogoApi'

const SEARCH_DEBOUNCE = 400

export function useCatalogoArticulos() {
  /* ===========================
   * Estados
   * =========================== */

  const [ramas, setRamas] = useState([])
  const [normas, setNormas] = useState([])

  const [search, setSearch] = useState('')
  const [searchDebounced, setSearchDebounced] = useState('')

  const [ramaId, setRamaId] = useState('')
  const [normaId, setNormaId] = useState('')

  const [ordering, setOrdering] = useState('norma')
  const [orderDir, setOrderDir] = useState('asc')

  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  const [articulos, setArticulos] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [totalPages, setTotalPages] = useState(1)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const [expanded, setExpanded] = useState(new Set())

  const firstLoad = useRef(true)

  /* ===========================
   * Opciones de filtros
   * =========================== */

  useEffect(() => {
    let mounted = true

    const load = async () => {
      try {
        const [r, n] = await Promise.all([
          catalogoApi.ramas(),
          catalogoApi.normas(),
        ])

        if (!mounted) return

        setRamas(r.data ?? [])
        setNormas(n.data ?? [])
      } catch (e) {
        console.error(e)
      }
    }

    load()

    return () => {
      mounted = false
    }
  }, [])

  /* ===========================
   * Debounce búsqueda
   * =========================== */

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchDebounced(search)
    }, SEARCH_DEBOUNCE)

    return () => clearTimeout(timer)
  }, [search])

  /* ===========================
   * Reset página
   * =========================== */

  useEffect(() => {
    if (firstLoad.current) return

    setPage(1)
  }, [
    searchDebounced,
    ramaId,
    normaId,
    ordering,
    orderDir,
    pageSize,
  ])

  /* ===========================
   * Cargar artículos
   * =========================== */

  const fetchArticulos = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const order =
        orderDir === 'desc'
          ? `-${ordering}`
          : ordering

      const { data } = await catalogoApi.articulos({
        page,
        page_size: pageSize,
        search: searchDebounced || undefined,
        rama_id: ramaId || undefined,
        norma_id: normaId || undefined,
        ordering: order,
      })

      if (Array.isArray(data)) {
        setArticulos(data)
        setTotalCount(data.length)
        setTotalPages(1)
      } else {
        setArticulos(data.results ?? [])
        setTotalCount(data.count ?? 0)
        setTotalPages(
          Math.max(
            1,
            Math.ceil((data.count ?? 0) / pageSize)
          )
        )
      }
    } catch (err) {
      console.error(err)
      setError('No se pudieron cargar los artículos.')
    } finally {
      setLoading(false)
      firstLoad.current = false
    }
  }, [
    page,
    pageSize,
    searchDebounced,
    ramaId,
    normaId,
    ordering,
    orderDir,
  ])

  useEffect(() => {
    fetchArticulos()
  }, [fetchArticulos])

  /* ===========================
   * Acciones
   * =========================== */

  const handleSort = useCallback((campo) => {
    setOrdering((prev) => {
      if (prev === campo) {
        setOrderDir((d) => (d === 'asc' ? 'desc' : 'asc'))
        return prev
      }

      setOrderDir('asc')
      return campo
    })
  }, [])

  const toggleExpand = useCallback((id) => {
    setExpanded((prev) => {
      const next = new Set(prev)

      if (next.has(id))
        next.delete(id)
      else
        next.add(id)

      return next
    })
  }, [])

  const resetFiltros = useCallback(() => {
    setSearch('')
    setRamaId('')
    setNormaId('')
    setOrdering('norma')
    setOrderDir('asc')
    setPage(1)
  }, [])

  const recargar = useCallback(() => {
    fetchArticulos()
  }, [fetchArticulos])

  /* ===========================
   * Derivados
   * =========================== */

  const hayFiltros = useMemo(
    () => Boolean(search || ramaId || normaId),
    [search, ramaId, normaId]
  )

  const firstItem = useMemo(
    () => (totalCount ? (page - 1) * pageSize + 1 : 0),
    [page, pageSize, totalCount]
  )

  const lastItem = useMemo(
    () => Math.min(page * pageSize, totalCount),
    [page, pageSize, totalCount]
  )

  const visiblePages = useMemo(() => {
    const delta = 2
    const pages = []

    for (
      let i = Math.max(1, page - delta);
      i <= Math.min(totalPages, page + delta);
      i++
    ) {
      pages.push(i)
    }

    return pages
  }, [page, totalPages])

  return {
    ramas,
    normas,

    search,
    setSearch,

    ramaId,
    setRamaId,

    normaId,
    setNormaId,

    ordering,
    orderDir,
    handleSort,

    page,
    setPage,

    pageSize,
    setPageSize,

    articulos,
    totalCount,
    totalPages,

    loading,
    error,

    expanded,
    toggleExpand,

    hayFiltros,
    firstItem,
    lastItem,
    visiblePages,

    resetFiltros,
    recargar,
  }
}