import { useCallback, useEffect, useState } from 'react'
import jurisprudenciaApi from '../../../api/jurisprudenciaApi'

export default function useListadoJurisprudencia(externo = false) {
  const [consulta, setConsulta] = useState(externo ? { palabras: 'penal' } : {})
  const [page, setPage] = useState(1)
  const [revision, setRevision] = useState(0)
  const [datos, setDatos] = useState({ results: [], count: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const recargar = useCallback(() => setRevision((v) => v + 1), [])
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError('')
    const solicitar = externo ? jurisprudenciaApi.buscarTSJ : jurisprudenciaApi.listar
    solicitar({ ...consulta, page, ...(!externo ? { page_size: 25 } : {}) }, { signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setDatos(data) })
      .catch((e) => { if (!controller.signal.aborted) setError(e.response?.data?.detail || 'No se pudo consultar el listado. Vuelve a intentar.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [externo, consulta, page, revision])
  return {
    ...datos, page, setPage, loading, error,
    totalPages: externo ? datos.total_pages || 1 : Math.ceil(datos.count / 25),
    buscar: (filtros) => { setPage(1); setConsulta(Object.fromEntries(Object.entries(filtros).filter(([, v]) => v !== ''))) },
    recargar,
  }
}
