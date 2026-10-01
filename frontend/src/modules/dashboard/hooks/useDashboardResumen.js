// modules/dashboard/hooks/useDashboardResumen.js
import { useCallback, useEffect, useState } from 'react'
import dashboardApi from '../../../api/dashboardApi'

const VACIO = {
  totales: { casos_activos: 0, casos_en_papelera: 0 },
  casos_por_etapa: [],
  casos_por_rama: [],
  estado_analisis: [],
  casos_por_usuario: [],
  casos_por_mes: [],
  normas_mas_consultadas: [],
}

export default function useDashboardResumen() {
  const [resumen, setResumen] = useState(VACIO)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await dashboardApi.resumen()
      setResumen(data)
    } catch (e) {
      setError('No se pudieron cargar las estadísticas.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return { resumen, loading, error, reload: load }
}
