import { CanceledError } from 'axios'

// Memoria de la pestaña: nunca persistir respuestas ni credenciales en disco.
const entries = new Map()
const MAX_ENTRIES = 60
const copy = (response) => ({ ...response, data: structuredClone(response.data) })

export function clearRequestCache() {
  entries.clear()
}

function forConsumer(promise, signal) {
  if (!signal) return promise.then(copy)
  if (signal.aborted) return Promise.reject(new CanceledError())
  return new Promise((resolve, reject) => {
    const abort = () => reject(new CanceledError())
    signal.addEventListener('abort', abort, { once: true })
    promise.then(value => {
      if (!signal.aborted) resolve(copy(value))
    }, reject).finally(() => signal.removeEventListener('abort', abort))
  })
}

export function cachedResponse(key, load, { ttl = 60000, signal } = {}) {
  if (signal?.aborted) return Promise.reject(new CanceledError())
  const previous = entries.get(key)
  if (previous && (previous.pending || previous.expires > Date.now())) {
    return forConsumer(previous.promise, signal)
  }
  entries.delete(key)
  if (entries.size >= MAX_ENTRIES) entries.delete(entries.keys().next().value)
  const entry = { pending: true, expires: 0 }
  entry.promise = Promise.resolve().then(load).then(response => {
    entry.pending = false
    entry.expires = Date.now() + ttl
    // Una petición anterior a un cambio no vuelve a llenar la caché invalidada.
    return copy(response)
  }, error => {
    if (entries.get(key) === entry) entries.delete(key)
    throw error
  })
  entries.set(key, entry)
  return forConsumer(entry.promise, signal)
}
