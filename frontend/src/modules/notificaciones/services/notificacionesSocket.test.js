import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { conectarNotificaciones } from './notificacionesSocket'
vi.mock('../../../api/tokenManager', () => ({ getAccessToken: () => 'token-de-prueba' }))
let instancia
beforeEach(() => {
  vi.useFakeTimers()
  vi.stubGlobal('WebSocket', class {
    constructor(url) { this.url = url; this.send = vi.fn(); this.close = vi.fn(); instancia = this }
  })
})
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.unstubAllEnvs() })

it('autentica por mensaje, recibe eventos y no hace sondeo cuando está conectado', () => {
  const recibir = vi.fn(), reconciliar = vi.fn()
  const cerrar = conectarNotificaciones({ recibir, reconciliar })
  expect(instancia.url).not.toContain('token')
  instancia.onopen()
  expect(instancia.send).toHaveBeenCalledWith(JSON.stringify({ access_token: 'token-de-prueba' }))
  instancia.onmessage({ data: JSON.stringify({ type: 'actualizadas', no_leidas: 3 }) })
  vi.advanceTimersByTime(120_000)
  expect(recibir).toHaveBeenCalledWith({ type: 'actualizadas', no_leidas: 3 })
  expect(reconciliar).not.toHaveBeenCalled()
  cerrar()
  expect(instancia.close).toHaveBeenCalled()
})

it('reconecta tras desconexión y cancela la reconexión al desmontar', async () => {
  const cerrar = conectarNotificaciones({ recibir: vi.fn(), reconciliar: vi.fn() })
  const anterior = instancia
  await anterior.onclose({ code: 1006 })
  await vi.advanceTimersByTimeAsync(1000)
  expect(instancia).not.toBe(anterior)
  await instancia.onclose({ code: 1006 })
  const actual = instancia
  cerrar()
  await vi.advanceTimersByTimeAsync(60_000)
  expect(instancia).toBe(actual)
})

it('reintenta si el constructor falla temporalmente', async () => {
  const socketClase = globalThis.WebSocket
  const constructor = vi.fn().mockImplementationOnce(() => { throw new Error('sin conexión') })
    .mockImplementation(function (url) { return new socketClase(url) })
  vi.stubGlobal('WebSocket', constructor)
  const cerrar = conectarNotificaciones({ recibir: vi.fn(), reconciliar: vi.fn() })
  await vi.advanceTimersByTimeAsync(1000)
  expect(constructor).toHaveBeenCalledTimes(2)
  cerrar()
})

it('no abandona la reconexión cuando falla la renovación de sesión', async () => {
  const reconciliar = vi.fn().mockRejectedValue(new Error('backend reiniciando'))
  const cerrar = conectarNotificaciones({ recibir: vi.fn(), reconciliar })
  const anterior = instancia
  await anterior.onclose({ code: 4401 })
  await vi.advanceTimersByTimeAsync(1000)
  expect(instancia).not.toBe(anterior)
  expect(reconciliar).toHaveBeenCalledTimes(1)
  cerrar()
})

it('cierra una conexión que no confirma autenticación y limpia sus temporizadores', () => {
  const cerrar = conectarNotificaciones({ recibir: vi.fn(), reconciliar: vi.fn() })
  vi.advanceTimersByTime(10_000)
  expect(instancia.close).toHaveBeenCalledTimes(1)
  cerrar()
  expect(vi.getTimerCount()).toBe(0)
})

it('usa el mismo origen de Docker y wss cuando la API es https', () => {
  vi.stubEnv('VITE_API_URL', '/')
  const cerrar = conectarNotificaciones({ recibir: vi.fn(), reconciliar: vi.fn() })
  expect(instancia.url).toBe(`ws://${window.location.host}/ws/notificaciones/`)
  cerrar()
  vi.stubEnv('VITE_API_URL', 'https://derecho.example')
  const cerrarSeguro = conectarNotificaciones({ recibir: vi.fn(), reconciliar: vi.fn() })
  expect(instancia.url).toBe('wss://derecho.example/ws/notificaciones/')
  cerrarSeguro()
})
