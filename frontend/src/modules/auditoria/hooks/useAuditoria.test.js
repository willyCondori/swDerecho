import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import useAuditoria from './useAuditoria'
import auditoriaApi from '../../../api/auditoriaApi'
vi.mock('../../../api/auditoriaApi', () => ({ default: { acciones: vi.fn(), listar: vi.fn() } }))
beforeEach(() => {
  vi.clearAllMocks()
  auditoriaApi.acciones.mockResolvedValue({ data: ['CREATE', 'UPDATE'] })
  auditoriaApi.listar.mockResolvedValue({ data: { results: [{ id: 1 }], count: 51 } })
  vi.spyOn(console, 'error').mockImplementation(() => {})
})
afterEach(() => vi.restoreAllMocks())
it('pagina la auditoría y transmite filtros sin conservar una página inválida', async () => {
  const { result } = renderHook(() => useAuditoria())
  await waitFor(() => expect(result.current.loading).toBe(false))
  expect(result.current.totalPages).toBe(3)
  act(() => result.current.setPage(2))
  await waitFor(() => expect(auditoriaApi.listar).toHaveBeenCalledWith({ page: 2, page_size: 25 }))
  act(() => result.current.setFiltro('accion', 'UPDATE'))
  await waitFor(() => expect(auditoriaApi.listar).toHaveBeenCalledWith({ page: 1, page_size: 25, accion: 'UPDATE' }))
  act(() => result.current.limpiarFiltros())
  expect(result.current.filtros.accion).toBe('')
})
it('informa el error de consulta', async () => {
  auditoriaApi.listar.mockRejectedValue(new Error('Sin conexión'))
  const { result } = renderHook(() => useAuditoria())
  await waitFor(() => expect(result.current.loading).toBe(false))
  expect(result.current.error).toContain('No se pudo cargar')
})
