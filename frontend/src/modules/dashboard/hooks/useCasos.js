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
      // Antes usaba casosApi.misCasos() (solo los del usuario logueado),
      // pero la tarjeta de arriba dice "Casos activos" a secas, no
      // "Mis casos" — con eso, un Abogado o Asistente que no es dueño
      // de ningún caso veía siempre 0, aunque sí hubiera actividad en
      // el sistema. Ahora usa el mismo endpoint que la página /casos
      // (todos los casos activos, visibles para los tres roles).
      const { data } = await casosApi.listar({ page_size: pageSize })
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