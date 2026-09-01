// modules/auditoria/hooks/useAuditoria.js
import { useCallback, useEffect, useState } from 'react'
import auditoriaApi from '../../../api/auditoriaApi'

const FILTROS_INICIALES = {
  tabla: '',
  accion: '',
  fecha_desde: '',
  fecha_hasta: '',
}

export default function useAuditoria() {
  const [registros, setRegistros] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [count, setCount] = useState(0)
  const [filtros, setFiltrosState] = useState(FILTROS_INICIALES)
  const [acciones, setAcciones] = useState([])

  useEffect(() => {
    auditoriaApi.acciones()
      .then(({ data }) => setAcciones(data ?? []))
      .catch(() => setAcciones([]))
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filtros.tabla) params.tabla = filtros.tabla
      if (filtros.accion) params.accion = filtros.accion
      if (filtros.fecha_desde) params.fecha_desde = filtros.fecha_desde
      if (filtros.fecha_hasta) params.fecha_hasta = filtros.fecha_hasta

      const { data } = await auditoriaApi.listar(params)
      if (Array.isArray(data)) {
        setRegistros(data)
        setCount(data.length)
      } else {
        setRegistros(data.results ?? [])
        setCount(data.count ?? data.results?.length ?? 0)
      }
    } catch (e) {
      console.error('Error cargando auditoría:', e, e?.response?.data)
      setError('No se pudo cargar el registro de auditoría.')
    } finally {
      setLoading(false)
    }
  }, [filtros])

  useEffect(() => {
    load()
  }, [load])

  const setFiltro = (campo, valor) => {
    setFiltrosState((prev) => ({ ...prev, [campo]: valor }))
  }

  const limpiarFiltros = () => setFiltrosState(FILTROS_INICIALES)

  return {
    registros,
    loading,
    error,
    count,
    filtros,
    setFiltro,
    limpiarFiltros,
    acciones,
    reload: load,
  }
}
