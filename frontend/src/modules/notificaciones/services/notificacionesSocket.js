import { getAccessToken } from '../../../api/tokenManager'

export function conectarNotificaciones({ recibir, reconciliar }) {
  let detenido = false, socket, reintento, respaldo, espera, intentos = 0
  const activarRespaldo = () => {
    if (!respaldo) respaldo = setInterval(reconciliar, 60_000)
  }
  const programarReconexion = () => {
    if (detenido) return
    clearTimeout(reintento)
    reintento = setTimeout(conectar, Math.min(30_000, 1000 * 2 ** Math.min(intentos++, 5)))
  }
  const conectar = () => {
    if (detenido) return
    if (typeof WebSocket === 'undefined') { activarRespaldo(); return }
    const base = new URL(import.meta.env.VITE_API_URL || 'http://localhost:8000', window.location.origin)
    base.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:'
    base.pathname = '/ws/notificaciones/'; base.search = ''; base.hash = ''
    try { socket = new WebSocket(base.href) } catch {
      activarRespaldo(); programarReconexion(); return
    }
    const actual = socket
    // Recuperar también conexiones abiertas que nunca reciben autenticación.
    espera = setTimeout(() => actual.close(), 10_000)
    actual.onopen = () => {
      if (!detenido) actual.send(JSON.stringify({ access_token: getAccessToken() }))
    }
    actual.onmessage = (evento) => {
      if (detenido || socket !== actual) return
      try {
        const datos = JSON.parse(evento.data)
        if (!['contador', 'actualizadas'].includes(datos.type) || !Number.isInteger(datos.no_leidas) || datos.no_leidas < 0) return
        intentos = 0
        clearTimeout(espera)
        clearInterval(respaldo); respaldo = null
        recibir(datos)
      } catch { /* Ignorar mensajes inválidos. */ }
    }
    actual.onclose = async (evento) => {
      if (detenido || socket !== actual) return
      clearTimeout(espera)
      activarRespaldo()
      // La petición autenticada renueva el JWT mediante el interceptor existente.
      try {
        if (evento.code === 4401) await reconciliar()
      } catch { /* Reintentar incluso si temporalmente falla también la API. */ }
      finally { programarReconexion() }
    }
    actual.onerror = () => { /* onclose inicia la reconexión. */ }
  }
  conectar()
  return () => {
    detenido = true
    clearTimeout(reintento); clearTimeout(espera); clearInterval(respaldo)
    socket?.close()
  }
}
