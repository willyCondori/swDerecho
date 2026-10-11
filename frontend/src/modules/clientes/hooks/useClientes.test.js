import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import useClientes from './useClientes'
import clientesApi from '../../../api/clientesApi'
vi.mock('../../../api/clientesApi', () => ({ default: { listar: vi.fn(), buscar: vi.fn(), eliminar: vi.fn() } }))
beforeEach(() => {
  vi.clearAllMocks()
  clientesApi.listar.mockResolvedValue({ data: { count: 21, results: [{ id: 1 }] } })
  vi.spyOn(console, 'error').mockImplementation(() => {})
})
afterEach(() => vi.restoreAllMocks())
it('pagina el listado y reinicia la página al buscar', async () => {
  const { result } = renderHook(() => useClientes())
  await waitFor(() => expect(result.current.loading).toBe(false))
  expect(result.current.totalPages).toBe(3)
  act(() => result.current.setPage(2))
  await waitFor(() => expect(clientesApi.listar).toHaveBeenCalledWith({ page: 2, page_size: 10 }))
  clientesApi.buscar.mockResolvedValue({ data: Array.from({ length: 11 }, (_, id) => ({ id })) })
  act(() => result.current.setSearch(' Pérez '))
  await waitFor(() => expect(result.current.count).toBe(11))
  expect(result.current.page).toBe(1)
  expect(result.current.clientes).toHaveLength(10)
  expect(clientesApi.buscar).toHaveBeenCalledWith('Pérez')
  act(() => result.current.setPage(2))
  expect(result.current.clientes).toHaveLength(1)
})
it('una respuesta antigua no sustituye una búsqueda reciente', async () => {
  let resolver
  clientesApi.listar.mockReturnValue(new Promise((resolve) => { resolver = resolve }))
  clientesApi.buscar.mockResolvedValue({ data: [{ id: 2 }] })
  const { result } = renderHook(() => useClientes())
  act(() => result.current.setSearch('Ana'))
  await waitFor(() => expect(result.current.clientes).toEqual([{ id: 2 }]))
  await act(async () => resolver({ data: { count: 100, results: [{ id: 1 }] } }))
  expect(result.current.clientes).toEqual([{ id: 2 }])
  expect(result.current.count).toBe(1)
})
it('muestra error y permite reintentar', async () => {
  clientesApi.listar.mockRejectedValueOnce(new Error('Sin conexión'))
  const { result } = renderHook(() => useClientes())
  await waitFor(() => expect(result.current.error).toBeTruthy())
  await act(async () => result.current.reload())
  expect(result.current.error).toBeNull()
  expect(result.current.count).toBe(21)
})
