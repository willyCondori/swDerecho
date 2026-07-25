// modules/usuarios/hooks/useRoles.js
import { useEffect, useState } from 'react'
import usuariosApi from '../../../api/usuariosApi'

/**
 * Carga el listado compacto de roles activos (GET /api/roles/lista/)
 * para usarlo en selects de formularios.
 */
export function useRoles() {
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let activo = true
    setLoading(true)
    usuariosApi.listarRoles()
      .then(({ data }) => {
        if (activo) setRoles(data ?? [])
      })
      .catch(() => {
        if (activo) setError('No se pudieron cargar los roles.')
      })
      .finally(() => {
        if (activo) setLoading(false)
      })
    return () => { activo = false }
  }, [])

  return { roles, loading, error }
}