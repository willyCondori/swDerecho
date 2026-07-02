// modules/usuarios/hooks/usePerfilUsuario.js
import { useCallback, useEffect, useState } from 'react'
import usuariosService from '../services/usuariosService'

const FORM_INICIAL = {
  nombreCompleto: '',
  email: '',
  telefono: '',
  profesion: '',
  biografia: '',
}

function extraerMensajeError(err) {
  const data = err.response?.data
  if (!data) return 'No se pudo guardar el perfil.'
  if (typeof data.detail === 'string') return data.detail
  const primerCampo = Object.values(data)[0]
  if (Array.isArray(primerCampo)) return primerCampo[0]
  return 'No se pudo guardar el perfil.'
}

/**
 * Carga el perfil del usuario indicado y expone el estado del
 * formulario para editarlo vía PATCH /api/usuarios/{id}/perfil/.
 *
 * NOTA: los nombres de campo (nombre_completo, telefono, profesion,
 * biografia) son un punto de partida razonable — ajústalos a los que
 * realmente exponga tu PerfilUsuarioWriteSerializer.
 */
export function usePerfilUsuario(usuarioId) {
  const [form, setForm] = useState(FORM_INICIAL)
  const [fieldErrors, setFieldErrors] = useState({})
  const [cargando, setCargando] = useState(true)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)
  const [guardado, setGuardado] = useState(false)

  useEffect(() => {
    if (!usuarioId) return
    let activo = true
    setCargando(true)
    usuariosService.obtener(usuarioId)
      .then(({ data }) => {
        if (!activo) return
        const perfil = data.perfil ?? {}
        setForm({
          nombreCompleto: perfil.nombre_completo ?? '',
          email: perfil.email ?? '',
          telefono: perfil.telefono ?? '',
          profesion: perfil.profesion ?? '',
          biografia: perfil.biografia ?? '',
        })
      })
      .catch(() => {
        if (activo) setError('No se pudo cargar el perfil.')
      })
      .finally(() => {
        if (activo) setCargando(false)
      })
    return () => { activo = false }
  }, [usuarioId])

  const handleChange = useCallback((e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    setFieldErrors((prev) => (prev[name] ? { ...prev, [name]: null } : prev))
  }, [])

  const validar = () => {
    const errores = {}
    if (!form.nombreCompleto.trim()) errores.nombreCompleto = 'El nombre completo es obligatorio.'
    if (form.email && !/^\S+@\S+\.\S+$/.test(form.email)) errores.email = 'Correo inválido.'
    return errores
  }

  const submit = async () => {
    const errores = validar()
    if (Object.keys(errores).length) {
      setFieldErrors(errores)
      return false
    }

    setEnviando(true)
    setError(null)
    setGuardado(false)
    try {
      await usuariosService.actualizarPerfil(usuarioId, {
        nombre_completo: form.nombreCompleto.trim(),
        email: form.email.trim() || null,
        telefono: form.telefono.trim() || null,
        profesion: form.profesion.trim() || null,
        biografia: form.biografia.trim() || null,
      })
      setGuardado(true)
      return true
    } catch (err) {
      setError(extraerMensajeError(err))
      return false
    } finally {
      setEnviando(false)
    }
  }

  return { form, fieldErrors, cargando, enviando, error, guardado, handleChange, submit }
}