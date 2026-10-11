import { beforeEach, expect, it, vi } from 'vitest'

let api, cachedGet, tokens, adapter, catalogo
beforeEach(async () => {
  vi.resetModules()
  const axios = (await import('axios')).default
  adapter = vi.fn(async config => ({ config, data: [{ id: 1 }], status: 200, statusText: 'OK', headers: {} }))
  axios.defaults.adapter = adapter
  api = (await import('./axiosInstance')).default
  cachedGet = (await import('./cachedGet')).default
  tokens = await import('./tokenManager')
  catalogo = (await import('./catalogoApi')).default
  tokens.setAccessToken('sesion-uno')
})

it('las dos formas de consultar ramas usan una sola petición', async () => {
  await Promise.all([catalogo.ramas(), catalogo.listaRamas()])
  await catalogo.ramas()
  expect(adapter).toHaveBeenCalledTimes(1)
})

it('guardar un cambio invalida los catálogos', async () => {
  await catalogo.ramas()
  await catalogo.actualizarRama(1, { nombre: 'Penal' })
  await catalogo.ramas()
  expect(adapter).toHaveBeenCalledTimes(3)
})

it('un cambio rechazado no invalida los datos que siguen vigentes', async () => {
  await catalogo.ramas()
  adapter.mockRejectedValueOnce(new Error('guardado rechazado'))
  await expect(catalogo.actualizarRama(1, {})).rejects.toThrow('guardado rechazado')
  await catalogo.ramas()
  expect(adapter).toHaveBeenCalledTimes(2)
})

it('roles, etapas y resoluciones también reutilizan su lectura', async () => {
  const usuarios = (await import('./usuariosApi')).default
  const casos = (await import('./casosApi')).default
  const jurisprudencia = (await import('./jurisprudenciaApi')).default
  for (let i = 0; i < 2; i++) {
    await usuarios.listarRoles()
    await casos.etapas()
    await jurisprudencia.obtener(123, { signal: new AbortController().signal })
  }
  expect(adapter).toHaveBeenCalledTimes(3)
})

it('cerrar o cambiar la sesión obliga a consultar con la nueva credencial', async () => {
  await catalogo.ramas()
  tokens.clearAccessToken()
  tokens.setAccessToken('sesion-dos')
  await catalogo.ramas()
  expect(adapter).toHaveBeenCalledTimes(2)
  expect(adapter.mock.calls[1][0].headers.Authorization).toBe('Bearer sesion-dos')
})

it('las consultas sin sesión y las forzadas no se almacenan', async () => {
  tokens.clearAccessToken()
  await cachedGet('/selector')
  await cachedGet('/selector')
  tokens.setAccessToken('sesion')
  await cachedGet('/selector', { cache: false })
  await cachedGet('/selector', { cache: false })
  expect(adapter).toHaveBeenCalledTimes(4)
})

it('clientes y progreso del análisis siguen consultándose directamente', async () => {
  for (let i = 0; i < 2; i++) {
    await api.get('/api/clientes/')
    await api.get('/api/casos/uuid/estado_analisis/')
  }
  expect(adapter).toHaveBeenCalledTimes(4)
})
