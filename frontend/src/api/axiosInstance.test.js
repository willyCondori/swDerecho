import { afterEach, beforeEach, expect, it, vi } from 'vitest'

let api, axios, tokens, adapter
const ok = (config, data = {}) => ({ config, data, status: 200, statusText: 'OK', headers: {} })
const unauthorized = (config) => Promise.reject(new axios.AxiosError(
  'Unauthorized', 'ERR_BAD_REQUEST', config, {}, { ...ok(config), status: 401 },
))

beforeEach(async () => {
  vi.resetModules()
  vi.stubEnv('VITE_API_URL', '/')
  axios = (await import('axios')).default
  adapter = vi.fn(async config => ok(config))
  axios.defaults.adapter = adapter
  api = (await import('./axiosInstance')).default
  tokens = await import('./tokenManager')
})

afterEach(() => vi.unstubAllEnvs())

it('no envía el access vencido al login, refresh ni recuperación', async () => {
  tokens.setAccessToken('vencido')
  for (const route of ['login/', 'refresh/', 'recuperar-password/', 'recuperar-password/confirmar/']) {
    await api.post(`/api/usuarios/auth/${route}`, {})
    expect(adapter.mock.calls.at(-1)[0].headers.Authorization).toBeUndefined()
  }
})

it('elimina encabezados heredados después de limpiar la sesión', async () => {
  api.defaults.headers.common.Authorization = 'Bearer anterior'
  tokens.clearAccessToken()
  await api.get('/api/casos/')
  expect(adapter.mock.calls.at(-1)[0].headers.Authorization).toBeUndefined()
})

it('renueva por la misma dirección de Docker y reintenta con el nuevo access', async () => {
  tokens.setAccessToken('vencido')
  adapter.mockImplementation(async config => {
    if (config.url.includes('/auth/refresh/')) {
      expect(axios.getUri(config)).toBe('/api/usuarios/auth/refresh/')
      expect(config.headers.Authorization).toBeUndefined()
      expect(config.withCredentials).toBe(true)
      return ok(config, { access_token: 'nuevo' })
    }
    if (config.headers.Authorization === 'Bearer vencido') return unauthorized(config)
    expect(config.headers.Authorization).toBe('Bearer nuevo')
    return ok(config, { recuperada: true })
  })
  expect((await api.get('/api/casos/')).data.recuperada).toBe(true)
  expect(tokens.getAccessToken()).toBe('nuevo')
  expect(adapter).toHaveBeenCalledTimes(3)
})

it('comparte una renovación entre peticiones simultáneas y solo reintenta una vez', async () => {
  tokens.setAccessToken('vencido')
  let finishRefresh
  const refreshed = new Promise(resolve => { finishRefresh = resolve })
  adapter.mockImplementation(async config => {
    if (config.url.includes('/auth/refresh/')) {
      await refreshed
      return ok(config, { access_token: 'nuevo' })
    }
    return unauthorized(config)
  })
  const results = Promise.allSettled([api.get('/api/casos/'), api.get('/api/documentos/')])
  await vi.waitFor(() => expect(adapter.mock.calls.filter(([c]) => c.url.includes('/auth/refresh/'))).toHaveLength(1))
  finishRefresh()
  expect((await results).every(result => result.status === 'rejected')).toBe(true)
  expect(adapter).toHaveBeenCalledTimes(5)
})
