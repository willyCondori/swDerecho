// modules/notificaciones/hooks/useNotificaciones.js
import { useCallback, useEffect, useRef, useState } from 'react'
import notificacionesApi from '../../../api/notificacionesApi'

const INTERVALO_POLLING_MS = 30_000

/**
 * Maneja el estado de la campanita: cuenta de no leídas (se refresca sola
 * cada 30s, sin que el usuario tenga que abrir el panel) y la lista de
 * notificaciones recientes (se carga solo cuando el panel se abre, para
 * no pedirle al backend una lista que nadie está viendo).
 */
export default function useNotificaciones() {
  const [noLeidas, setNoLeidas] = useState(0)
  const [lista, setLista] = useState([])
  const [loadingLista, setLoadingLista] = useState(false)
  const montado = useRef(true)

  const cargarContador = useCallback(async () => {
    try {
      const { data } = await notificacionesApi.noLeidasCount()
      if (montado.current) setNoLeidas(data.no_leidas)
    } catch {
      // Si falla el polling no hace falta avisarle nada al usuario — se
      // reintenta solo en el próximo ciclo.
    }
  }, [])

  const cargarLista = useCallback(async () => {
    setLoadingLista(true)
    try {
      const { data } = await notificacionesApi.listar({ page_size: 10 })
      if (montado.current) setLista(data.results ?? [])
    } catch {
      if (montado.current) setLista([])
    } finally {
      if (montado.current) setLoadingLista(false)
    }
  }, [])

  useEffect(() => {
    montado.current = true
    cargarContador()
    const intervalo = setInterval(cargarContador, INTERVALO_POLLING_MS)
    return () => {
      montado.current = false
      clearInterval(intervalo)
    }
  }, [cargarContador])

  const marcarLeida = useCallback(async (id) => {
    setLista((prev) => prev.map((n) => (n.id === id ? { ...n, leida: true } : n)))
    setNoLeidas((prev) => Math.max(0, prev - 1))
    try {
      await notificacionesApi.marcarLeida(id)
    } catch {
      cargarContador()
      cargarLista()
    }
  }, [cargarContador, cargarLista])

  const marcarTodasLeidas = useCallback(async () => {
    setLista((prev) => prev.map((n) => ({ ...n, leida: true })))
    setNoLeidas(0)
    try {
      await notificacionesApi.marcarTodasLeidas()
    } catch {
      cargarContador()
      cargarLista()
    }
  }, [cargarContador, cargarLista])

  return { noLeidas, lista, loadingLista, cargarLista, marcarLeida, marcarTodasLeidas }
}
