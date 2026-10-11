import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import useNotificaciones from './useNotificaciones'
import api from '../../../api/notificacionesApi'
import { conectarNotificaciones } from '../services/notificacionesSocket'
vi.mock('../services/notificacionesSocket', () => ({ conectarNotificaciones: vi.fn() }))
vi.mock('../../../api/notificacionesApi', () => ({ default: {
  noLeidasCount: vi.fn(), listar: vi.fn(), marcarLeida: vi.fn(), marcarTodasLeidas: vi.fn(),
} }))
beforeEach(() => {
  vi.clearAllMocks()
  conectarNotificaciones.mockReturnValue(vi.fn())
  api.noLeidasCount.mockResolvedValue({ data: { no_leidas: 2 } })
  api.listar.mockResolvedValue({ data: { results: [{ id: 1, leida: false }, { id: 2, leida: true }] } })
  api.marcarLeida.mockResolvedValue({})
})
afterEach(() => vi.restoreAllMocks())
it('carga el contador y consulta la lista solo al abrirla', async () => {
  const { result } = renderHook(() => useNotificaciones())
  await waitFor(() => expect(result.current.noLeidas).toBe(2))
  expect(api.listar).not.toHaveBeenCalled()
  await act(async () => result.current.cargarLista())
  expect(result.current.lista).toHaveLength(2)
})
it('no descuenta una notificación que ya estaba leída', async () => {
  const { result } = renderHook(() => useNotificaciones())
  await waitFor(() => expect(result.current.noLeidas).toBe(2))
  await act(async () => result.current.cargarLista())
  await act(async () => result.current.marcarLeida(2))
  expect(result.current.noLeidas).toBe(2)
  expect(api.marcarLeida).not.toHaveBeenCalled()
})
it('marca una sola vez aunque se pulse dos veces durante la petición', async () => {
  let resolver
  api.marcarLeida.mockReturnValue(new Promise((resolve) => { resolver = resolve }))
  const { result } = renderHook(() => useNotificaciones())
  await waitFor(() => expect(result.current.noLeidas).toBe(2))
  await act(async () => result.current.cargarLista())
  let pendiente
  act(() => { pendiente = result.current.marcarLeida(1); result.current.marcarLeida(1) })
  expect(api.marcarLeida).toHaveBeenCalledTimes(1)
  expect(result.current.noLeidas).toBe(1)
  await act(async () => { resolver({}); await pendiente })
})
it('recupera el estado del servidor si falla la escritura', async () => {
  api.marcarLeida.mockRejectedValue(new Error('Sin conexión'))
  const { result } = renderHook(() => useNotificaciones())
  await waitFor(() => expect(result.current.noLeidas).toBe(2))
  await act(async () => result.current.cargarLista())
  await act(async () => result.current.marcarLeida(1))
  await waitFor(() => expect(result.current.noLeidas).toBe(2))
  expect(result.current.lista[0].leida).toBe(false)
})
it('cierra la conexión al desmontar', () => {
  const detener = vi.fn()
  conectarNotificaciones.mockReturnValue(detener)
  const { unmount } = renderHook(() => useNotificaciones())
  unmount()
  expect(detener).toHaveBeenCalled()
})

it('un evento más reciente no se sobrescribe con una petición HTTP anterior', async () => {
  let resolver
  api.noLeidasCount.mockReturnValue(new Promise((r) => { resolver = r }))
  const { result } = renderHook(() => useNotificaciones())
  const { recibir } = conectarNotificaciones.mock.calls[0][0]
  act(() => recibir({ type: 'actualizadas', no_leidas: 3 }))
  await act(async () => resolver({ data: { no_leidas: 2 } }))
  expect(result.current.noLeidas).toBe(3)
  expect(api.listar).not.toHaveBeenCalled()
})

it('refresca la lista por eventos únicamente con la campana abierta', async () => {
  const { rerender } = renderHook(({ abierto }) => useNotificaciones(abierto), { initialProps: { abierto: false } })
  const { recibir } = conectarNotificaciones.mock.calls[0][0]
  await act(async () => recibir({ type: 'actualizadas', no_leidas: 3 }))
  expect(api.listar).not.toHaveBeenCalled()
  rerender({ abierto: true })
  await act(async () => recibir({ type: 'actualizadas', no_leidas: 4 }))
  expect(api.listar).toHaveBeenCalledTimes(1)
})
