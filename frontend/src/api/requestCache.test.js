import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cachedResponse, clearRequestCache } from './requestCache'

const response = () => ({ data: { rows: [{ id: 1 }] }, status: 200 })
beforeEach(() => { clearRequestCache(); vi.useFakeTimers() })
afterEach(() => vi.useRealTimers())

it('comparte consultas simultáneas y devuelve copias independientes', async () => {
  const load = vi.fn(async () => response())
  const [a, b] = await Promise.all([cachedResponse('ramas', load), cachedResponse('ramas', load)])
  a.data.rows[0].id = 99
  expect(b.data.rows[0].id).toBe(1)
  expect((await cachedResponse('ramas', load)).data.rows[0].id).toBe(1)
  expect(load).toHaveBeenCalledTimes(1)
})

it('vuelve a consultar al vencer el plazo', async () => {
  const load = vi.fn(async () => response())
  await cachedResponse('ramas', load, { ttl: 1000 })
  vi.advanceTimersByTime(1000)
  await cachedResponse('ramas', load, { ttl: 1000 })
  expect(load).toHaveBeenCalledTimes(2)
})

it('no conserva errores y permite reintentar', async () => {
  const load = vi.fn().mockRejectedValueOnce(new Error('red')).mockResolvedValue(response())
  await expect(cachedResponse('ramas', load)).rejects.toThrow('red')
  await cachedResponse('ramas', load)
  expect(load).toHaveBeenCalledTimes(2)
})

it('una respuesta tardía no restaura datos anteriores a la invalidación', async () => {
  let finish
  const old = cachedResponse('ramas', () => new Promise(resolve => { finish = resolve }))
  await Promise.resolve()
  clearRequestCache()
  const fresh = vi.fn(async () => ({ data: { version: 2 } }))
  await cachedResponse('ramas', fresh)
  finish(response())
  await old
  expect((await cachedResponse('ramas', fresh)).data.version).toBe(2)
  expect(fresh).toHaveBeenCalledTimes(1)
})

it('cancelar un lector no cancela la consulta de otro lector', async () => {
  let finish
  const load = vi.fn(() => new Promise(resolve => { finish = resolve }))
  const controller = new AbortController()
  const first = cachedResponse('resolucion', load, { signal: controller.signal })
  const second = cachedResponse('resolucion', load)
  const rejected = expect(first).rejects.toMatchObject({ code: 'ERR_CANCELED' })
  await Promise.resolve()
  controller.abort()
  finish(response())
  await rejected
  expect((await second).data.rows).toHaveLength(1)
  expect(load).toHaveBeenCalledTimes(1)
})

it('un consumidor ya cancelado no inicia peticiones', async () => {
  const load = vi.fn()
  const controller = new AbortController()
  controller.abort()
  await expect(cachedResponse('ramas', load, { signal: controller.signal })).rejects.toMatchObject({ code: 'ERR_CANCELED' })
  expect(load).not.toHaveBeenCalled()
})

it('limita el número de resoluciones retenidas en memoria', async () => {
  for (let i = 0; i < 61; i++) await cachedResponse(`resolucion:${i}`, async () => response())
  const load = vi.fn(async () => response())
  await cachedResponse('resolucion:0', load)
  expect(load).toHaveBeenCalledTimes(1)
})
