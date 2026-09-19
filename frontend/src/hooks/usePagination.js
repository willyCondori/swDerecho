// hooks/usePagination.js
import { useCallback, useState } from 'react'

/**
 * Estado de paginación reutilizable para listas administradas por la API
 * (DRF PageNumberPagination: `page` + `page_size`, respuesta { count, results }).
 *
 * Uso típico dentro de un hook de listado:
 *   const { page, setPage, count, setCount, totalPages, pageSize, resetPage, retrocederSiVacia }
 *     = usePagination(10)
 */
export default function usePagination(pageSize = 10) {
  const [page, setPage] = useState(1)
  const [count, setCount] = useState(0)

  const totalPages = Math.max(1, Math.ceil(count / pageSize))
  const resetPage = useCallback(() => setPage(1), [])

  /**
   * Si al eliminar/cambiar de estado el último registro de la página actual,
   * DRF responde 404 ("Invalid page") para esa página. En ese caso se retrocede
   * una página en lugar de mostrar un error. Devuelve true si retrocedió.
   */
  const retrocederSiVacia = useCallback(
    (err) => {
      if (err?.response?.status === 404 && page > 1) {
        setPage((p) => Math.max(1, p - 1))
        return true
      }
      return false
    },
    [page]
  )

  return { page, setPage, count, setCount, totalPages, pageSize, resetPage, retrocederSiVacia }
}
