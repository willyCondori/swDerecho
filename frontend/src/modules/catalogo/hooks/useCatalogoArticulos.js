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
  const [numeroArticulo, setNumeroArticulo] = useState('')
  const [numeroDebounced, setNumeroDebounced] = useState('')
  const solicitudActual = useRef(0)
  const abortar = useRef(null)

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
      setNumeroDebounced(numeroArticulo)
    }, SEARCH_DEBOUNCE)

    return () => clearTimeout(timer)
  }, [search, numeroArticulo])

  /* ===========================
   * Reset página
   * =========================== */

  useEffect(() => {
    if (firstLoad.current) return

    setPage(1)
  }, [
    searchDebounced,
    numeroDebounced,
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
    const solicitud = ++solicitudActual.current
    abortar.current?.abort()
    const controller = new AbortController()
    abortar.current = controller
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
        numero_articulo: numeroDebounced.trim() || undefined,
        rama_id: ramaId || undefined,
        norma_id: normaId || undefined,
        ordering: order,
      }, controller.signal)
      if (solicitud !== solicitudActual.current) return

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
      if (solicitud !== solicitudActual.current || controller.signal.aborted) return
      console.error(err)
      setError('No se pudieron cargar los artículos.')
    } finally {
      if (solicitud === solicitudActual.current) {
        setLoading(false)
        firstLoad.current = false
      }
    }
  }, [
    page,
    pageSize,
    searchDebounced,
    numeroDebounced,
    ramaId,
    normaId,
    ordering,
    orderDir,
  ])

  const invalidarSolicitud = useCallback(() => { solicitudActual.current++ }, [])
  useEffect(() => {
    fetchArticulos()
    const controller = abortar.current
    return () => { invalidarSolicitud(); controller?.abort() }
  }, [fetchArticulos, invalidarSolicitud])

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

  const resetFiltros = useCallback(() => {
    setSearch('')
    setSearchDebounced('')
    setNumeroArticulo('')
    setNumeroDebounced('')
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
    () => Boolean(search || numeroArticulo || ramaId || normaId),
    [search, numeroArticulo, ramaId, normaId]
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
    numeroArticulo, setNumeroArticulo,
    buscando: search !== searchDebounced || numeroArticulo !== numeroDebounced,

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


    hayFiltros,
    firstItem,
    lastItem,
    visiblePages,

    resetFiltros,
    recargar,
  }
}
