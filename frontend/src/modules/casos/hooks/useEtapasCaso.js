// modules/casos/hooks/useEtapasCaso.js
import { useEffect, useState } from 'react'
import casosApi from '../../../api/casosApi'

// El catálogo es fijo y chico: se pide una sola vez por sesión y se
// comparte entre el filtro del listado y el formulario del detalle.
let cache = null
let pendiente = null

function cargarEtapas() {
  if (cache) return Promise.resolve(cache)
  if (!pendiente) {
    pendiente = casosApi
      .etapas()
      .then(({ data }) => {
        cache = Array.isArray(data) ? data : []
        return cache
      })
      .finally(() => {
        pendiente = null
      })
  }
  return pendiente
}

export default function useEtapasCaso(habilitado = true) {
  const [etapas, setEtapas] = useState(cache ?? [])

  useEffect(() => {
    if (!habilitado || cache) {
      if (cache) setEtapas(cache)
      return
    }
    let activo = true
    cargarEtapas()
      .then((lista) => activo && setEtapas(lista))
      .catch(() => activo && setEtapas([]))
    return () => {
      activo = false
    }
  }, [habilitado])

  return etapas
}
