import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import catalogoApi from '../../../api/catalogoApi'
import { useCatalogoArticulos } from './useCatalogoArticulos'

vi.mock('../../../api/catalogoApi', () => ({ default: { ramas: vi.fn(), normas: vi.fn(), articulos: vi.fn() } }))
beforeEach(() => {
  vi.useFakeTimers()
  vi.clearAllMocks()
  catalogoApi.ramas.mockResolvedValue({ data: [] })
  catalogoApi.normas.mockResolvedValue({ data: [] })
  catalogoApi.articulos.mockResolvedValue({ data: { results: [], count: 0 } })
})
afterEach(() => vi.useRealTimers())

it('envía número exacto con debounce y limpia todos los filtros', async () => {
  const { result, unmount } = renderHook(() => useCatalogoArticulos())
  await act(async () => {})
  act(() => { result.current.setNumeroArticulo('2 bis'); result.current.setRamaId('7') })
  expect(result.current.buscando).toBe(true)
  await act(async () => { await vi.advanceTimersByTimeAsync(400) })
  expect(catalogoApi.articulos.mock.calls.at(-1)[0]).toMatchObject({ numero_articulo: '2 bis', rama_id: '7', page: 1 })
  await act(async () => result.current.resetFiltros())
  expect(result.current.hayFiltros).toBe(false)
  expect(catalogoApi.articulos.mock.calls.at(-1)[0].numero_articulo).toBeUndefined()
  unmount()
})

it('una respuesta atrasada no reemplaza los resultados de una búsqueda más reciente', async () => {
  let resolverAntigua
  catalogoApi.articulos.mockImplementationOnce(() => new Promise((resolve) => { resolverAntigua = resolve }))
  const { result, unmount } = renderHook(() => useCatalogoArticulos())
  await act(async () => {})
  catalogoApi.articulos.mockResolvedValue({ data: { results: [{ id: 2 }], count: 1 } })
  await act(async () => result.current.recargar())
  expect(result.current.articulos).toEqual([{ id: 2 }])
  await act(async () => resolverAntigua({ data: { results: [{ id: 1 }], count: 1 } }))
  expect(result.current.articulos).toEqual([{ id: 2 }])
  expect(result.current.loading).toBe(false)
  unmount()
})
