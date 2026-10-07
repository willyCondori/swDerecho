import { useCallback, useSyncExternalStore } from 'react'
import useAuthStore from '../../auth/store/authStore'

const borradores = new Map()
const listeners = new Set()
useAuthStore.subscribe((actual, anterior) => {
  if (actual.user?.id !== anterior.user?.id) {
    borradores.clear()
    listeners.forEach((fn) => fn())
  }
})
// Conserva el File y los campos durante la navegación dentro de la sesión.
// Limpiar, iniciar la carga o cambiar de usuario descarta el borrador.
export function useBorradorCarga(formInicial) {
  const usuario = useAuthStore((s) => s.user?.id)
  const vacio = useCallback(() => ({ form: { ...formInicial }, archivo: null, modo: 'articulos', seleccion: [], revisionSeleccion: null }), [formInicial])
  const snapshot = useCallback(() => {
    if (!borradores.has(usuario)) borradores.set(usuario, vacio())
    return borradores.get(usuario)
  }, [usuario, vacio])
  const borrador = useSyncExternalStore(useCallback((fn) => { listeners.add(fn); return () => listeners.delete(fn) }, []), snapshot)
  const actualizar = useCallback((cambio) => {
    const actual = snapshot()
    borradores.set(usuario, { ...actual, ...(typeof cambio === 'function' ? cambio(actual) : cambio) })
    listeners.forEach((fn) => fn())
  }, [usuario, snapshot])
  const limpiar = useCallback(() => actualizar(vacio()), [actualizar, vacio])
  return { borrador, actualizar, limpiar }
}
