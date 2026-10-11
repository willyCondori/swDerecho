import api from './axiosInstance'
import { getAccessToken } from './tokenManager'
import { cachedResponse } from './requestCache'

// Solo endpoints elegidos explícitamente. No almacenar clientes, casos ni PDFs.
export default function cachedGet(url, { ttl = 60000, signal, cache = true, ...config } = {}) {
  if (!getAccessToken() || !cache || Object.keys(config).length) return api.get(url, { ...config, signal })
  return cachedResponse(url, () => api.get(url, config), { ttl, signal })
}
