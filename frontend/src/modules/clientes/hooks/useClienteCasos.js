// modules/clientes/hooks/useClienteCasos.js
import { useCallback, useEffect, useState } from 'react'
import clientesApi from '../../../api/clientesApi'

export default function useClienteCasos(id) {
  const [cliente, setCliente] = useState(null)
  const [casos, setCasos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const cargar = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [resCliente, resCasos] = await Promise.all([
        clientesApi.obtener(id),
        clientesApi.casos(id, { page_size: 50 }),
      ])
      setCliente(resCliente.data)

      const data = resCasos.data
      setCasos(Array.isArray(data) ? data : (data.results ?? []))
    } catch (e) {
      console.error('Error cargando cliente/casos:', e, e?.response?.data)
      setError('No se pudo cargar la información del cliente.')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    cargar()
  }, [cargar])

  return { cliente, casos, loading, error, reload: cargar }
}