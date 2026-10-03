import { useEffect, useState } from 'react'
import clientesApi from '../../../api/clientesApi'

export default function useBuscarClientes(query) {
  const [resultados, setResultados] = useState([])
  const [buscando, setBuscando] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const texto = query.trim()
    setResultados([])
    setError(null)
    if (texto.length < 2) {
      setBuscando(false)
      return
    }

    let vigente = true
    const controller = new AbortController()
    setBuscando(true)
    const timeoutId = setTimeout(async () => {
      try {
        const { data } = await clientesApi.buscar(texto, {
          signal: controller.signal, limit: 20, compacto: true,
        })
        if (vigente) setResultados(data)
      } catch {
        if (vigente) setError('No se pudieron buscar los clientes.')
      } finally {
        if (vigente) setBuscando(false)
      }
    }, 350)

    return () => {
      vigente = false
      clearTimeout(timeoutId)
      controller.abort()
    }
  }, [query])

  return { resultados, buscando, error }
}
