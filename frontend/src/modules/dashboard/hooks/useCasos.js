// modules/dashboard/hooks/useCasos.js
import { useCallback, useEffect, useState } from 'react'
import casosApi from '../../../api/casosApi'

export default function useCasos({ pageSize = 20 } = {}) {
  const [casos, setCasos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await casosApi.misCasos({ page_size: pageSize })
      setCasos(data.results ?? data)
    } catch (e) {
      setError('No se pudieron cargar los casos.')
    } finally {
      setLoading(false)
    }
  }, [pageSize])

  useEffect(() => {
    load()
  }, [load])

  return { casos, loading, error, reload: load }
}