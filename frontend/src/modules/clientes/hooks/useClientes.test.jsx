import { afterEach, expect, it, vi } from 'vitest'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import useClientes from './useClientes'
const api = vi.hoisted(() => ({ listar: vi.fn(), buscar: vi.fn() }))
vi.mock('../../../api/clientesApi', () => ({ default: api }))
afterEach(cleanup)
it('pagina los resultados de búsqueda sin repetir la petición al avanzar', async () => {
  api.listar.mockResolvedValue({ data: { count: 0, results: [] } })
  api.buscar.mockResolvedValue({ data: Array.from({ length: 23 }, (_, index) => ({ id: index + 1, nombres: 'Ana' })) })
  const { result } = renderHook(() => useClientes())
  await waitFor(() => expect(result.current.loading).toBe(false))
  act(() => result.current.setSearch('Ana'))
  await waitFor(() => expect(result.current.count).toBe(23))
  expect(result.current.clientes).toHaveLength(10)
  expect(result.current.totalPages).toBe(3)
  act(() => result.current.setPage(3))
  expect(result.current.clientes).toHaveLength(3)
  expect(result.current.clientes[0].id).toBe(21)
  expect(api.buscar).toHaveBeenCalledTimes(1)
  act(() => result.current.setSearch(''))
  await waitFor(() => expect(result.current.count).toBe(0))
  expect(result.current.page).toBe(1)
})
