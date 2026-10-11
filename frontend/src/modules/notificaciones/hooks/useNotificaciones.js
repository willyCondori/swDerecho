// modules/notificaciones/hooks/useNotificaciones.js
import { useCallback, useEffect, useRef, useState } from 'react'
import notificacionesApi from '../../../api/notificacionesApi'
import { conectarNotificaciones } from '../services/notificacionesSocket'


/**
 * Maneja el estado de la campanita: cuenta de no leídas (se refresca sola
 * por WebSocket, sin que el usuario tenga que abrir el panel) y la lista de
 * notificaciones recientes (se carga solo cuando el panel se abre, para
 * no pedirle al backend una lista que nadie está viendo).
 */
export default function useNotificaciones(abierto = false) {
  const [noLeidas, setNoLeidas] = useState(0)
  const [lista, setLista] = useState([])
  const [loadingLista, setLoadingLista] = useState(false)
  const montado = useRef(true)
  const marcando = useRef(new Set())
  const revisionContador = useRef(0)
  const panelAbierto = useRef(abierto)
  useEffect(() => { panelAbierto.current = abierto }, [abierto])

  const cargarContador = useCallback(async () => {
    const revision = revisionContador.current
    try {
      const { data } = await notificacionesApi.noLeidasCount()
      if (montado.current && revision === revisionContador.current) setNoLeidas(data.no_leidas)
    } catch {
      // La reconexión y el respaldo recuperan el contador si falta conexión.
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
    const desconectar = conectarNotificaciones({
      reconciliar: cargarContador,
      recibir: (datos) => {
        if (!montado.current) return
        revisionContador.current += 1
        setNoLeidas(datos.no_leidas)
        if (datos.type === 'actualizadas' && panelAbierto.current) cargarLista()
      },
    })
    return () => {
      montado.current = false
      desconectar()
    }
  }, [cargarContador, cargarLista])

  const marcarLeida = useCallback(async (id) => {
    const notificacion = lista.find((n) => n.id === id)
    if (notificacion?.leida || marcando.current.has(id)) return
    marcando.current.add(id)
    setLista((prev) => prev.map((n) => (n.id === id ? { ...n, leida: true } : n)))
    if (notificacion) setNoLeidas((prev) => Math.max(0, prev - 1))
    try {
      await notificacionesApi.marcarLeida(id)
      if (!notificacion) await cargarContador()
    } catch {
      cargarContador()
      cargarLista()
    } finally {
      marcando.current.delete(id)
    }
  }, [lista, cargarContador, cargarLista])

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
