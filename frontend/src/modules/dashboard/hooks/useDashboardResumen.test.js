import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import useDashboardResumen from './useDashboardResumen'
import dashboardApi from '../../../api/dashboardApi'
vi.mock('../../../api/dashboardApi', () => ({ default: { resumen: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())
it('muestra el resumen real sin calcularlo a partir de una página parcial', async () => {
  const data = { totales: { casos_activos: 123, casos_en_papelera: 4 } }
  dashboardApi.resumen.mockResolvedValue({ data })
  const { result } = renderHook(() => useDashboardResumen())
  await waitFor(() => expect(result.current.loading).toBe(false))
  expect(result.current.resumen).toEqual(data)
})
it('informa fallo y recupera el resumen al reintentar', async () => {
  dashboardApi.resumen.mockRejectedValueOnce(new Error('Sin conexión'))
  const { result } = renderHook(() => useDashboardResumen())
  await waitFor(() => expect(result.current.error).toBeTruthy())
  dashboardApi.resumen.mockResolvedValue({ data: { totales: { casos_activos: 3 } } })
  await act(async () => result.current.reload())
  expect(result.current.error).toBeNull()
  expect(result.current.resumen.totales.casos_activos).toBe(3)
})
