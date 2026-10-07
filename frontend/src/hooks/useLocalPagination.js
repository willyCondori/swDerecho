import { useState } from 'react'

/** Pagination for an entire in-memory collection, never for an API page. */
export default function useLocalPagination(rows, initialPageSize = 10) {
  const [state, setState] = useState({ rows, page: 1, pageSize: initialPageSize })
  const pageSize = state.pageSize
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize))
  const page = state.rows === rows ? Math.min(state.page, totalPages) : 1
  const setPage = (next) => setState({ rows, page: Math.max(1, Math.min(totalPages, next)), pageSize })
  const setPageSize = (next) => setState({ rows, page: 1, pageSize: next })
  return { page, pageSize, totalPages, setPage, setPageSize,
    visibleRows: rows.slice((page - 1) * pageSize, page * pageSize) }
}
