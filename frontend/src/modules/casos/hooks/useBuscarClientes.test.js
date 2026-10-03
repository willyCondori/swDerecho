import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import clientesApi from '../../../api/clientesApi'
import useBuscarClientes from './useBuscarClientes'

vi.mock('../../../api/clientesApi', () => ({ default: { buscar: vi.fn() } }))

beforeEach(() => {
  vi.useFakeTimers()
  vi.resetAllMocks()
})

afterEach(() => vi.useRealTimers())

async function esperarBusqueda() {
  await act(async () => { await vi.advanceTimersByTimeAsync(350) })
}

function pendiente() {
  let resolve
  let reject
  const promise = new Promise((resolver, rechazar) => { resolve = resolver; reject = rechazar })
  return { promise, resolve, reject }
}

describe('useBuscarClientes', () => {
  it('agrupa pulsaciones y solo solicita hasta 20 resultados compactos', async () => {
    clientesApi.buscar.mockResolvedValue({ data: [{ id: 1, nombre_completo: 'Ana Quispe' }] })
    const { result, rerender } = renderHook(({ query }) => useBuscarClientes(query), { initialProps: { query: 'a' } })
    rerender({ query: 'an' })
    rerender({ query: 'ana' })
    expect(clientesApi.buscar).not.toHaveBeenCalled()
    await esperarBusqueda()
    expect(clientesApi.buscar).toHaveBeenCalledExactlyOnceWith('ana', {
      signal: expect.any(AbortSignal), limit: 20, compacto: true,
    })
    expect(result.current.resultados).toEqual([{ id: 1, nombre_completo: 'Ana Quispe' }])
    expect(result.current.buscando).toBe(false)
  })

  it('cancela la petición anterior e ignora su respuesta tardía', async () => {
    const vieja = pendiente()
    const nueva = pendiente()
    clientesApi.buscar.mockReturnValueOnce(vieja.promise).mockReturnValueOnce(nueva.promise)
    const { result, rerender } = renderHook(({ query }) => useBuscarClientes(query), { initialProps: { query: 'ana' } })
    await esperarBusqueda()
    const signalAnterior = clientesApi.buscar.mock.calls[0][1].signal
    rerender({ query: 'maria' })
    expect(signalAnterior.aborted).toBe(true)
    await esperarBusqueda()
    await act(async () => { nueva.resolve({ data: [{ id: 2, nombre_completo: 'Maria Perez' }] }) })
    await act(async () => { vieja.resolve({ data: [{ id: 1, nombre_completo: 'Ana Quispe' }] }) })
    expect(result.current.resultados).toEqual([{ id: 2, nombre_completo: 'Maria Perez' }])
    expect(result.current.buscando).toBe(false)
  })

  it('vaciar el texto cancela la búsqueda y no permite que reaparezcan resultados viejos', async () => {
    const vieja = pendiente()
    clientesApi.buscar.mockReturnValue(vieja.promise)
    const { result, rerender } = renderHook(({ query }) => useBuscarClientes(query), { initialProps: { query: 'ana' } })
    await esperarBusqueda()
    const signal = clientesApi.buscar.mock.calls[0][1].signal
    rerender({ query: '' })
    expect(signal.aborted).toBe(true)
    await act(async () => { vieja.resolve({ data: [{ id: 1 }] }) })
    expect(result.current.resultados).toEqual([])
    expect(result.current.buscando).toBe(false)
  })

  it('distingue los fallos de búsqueda y los limpia al reintentar', async () => {
    clientesApi.buscar.mockRejectedValueOnce(new Error('Sin conexión')).mockResolvedValueOnce({ data: [] })
    const { result, rerender } = renderHook(({ query }) => useBuscarClientes(query), { initialProps: { query: 'ana' } })
    await esperarBusqueda()
    expect(result.current.error).toBe('No se pudieron buscar los clientes.')
    rerender({ query: 'maria' })
    await esperarBusqueda()
    expect(result.current.error).toBeNull()
    expect(result.current.buscando).toBe(false)
  })

  it('desmontar el selector cancela la petición y sus temporizadores', async () => {
    const vieja = pendiente()
    clientesApi.buscar.mockReturnValue(vieja.promise)
    const { unmount } = renderHook(() => useBuscarClientes('ana'))
    await esperarBusqueda()
    const signal = clientesApi.buscar.mock.calls[0][1].signal
    unmount()
    expect(signal.aborted).toBe(true)
    await act(async () => { vieja.reject(new Error('Cancelada')) })
  })
})
