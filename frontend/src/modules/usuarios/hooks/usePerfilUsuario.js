// modules/usuarios/hooks/usePerfilUsuario.js
import { useCallback, useEffect, useState } from 'react'
import usuariosApi from '../../../api/usuariosApi'

// Espeja 1:1 los campos de PerfilUsuarioWriteSerializer
// (backend/modulo_usuarios/serializers/usuario_serializer.py).
// Todas las claves arrancan con un valor definido a propósito:
// si alguna quedara en `undefined` acá, el input correspondiente
// nace "no controlado" y React tira el warning de
// "changing an uncontrolled input to be controlled" en cuanto
// handleChange le asigna el primer valor real.
const FORM_INICIAL = {
  nombres: '',
  apellidos: '',
  email: '',
  telefono: '',
  estado: true,
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
 * Campos alineados con PerfilUsuarioWriteSerializer: nombres,
 * apellidos, email, telefono, estado.
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
    usuariosApi.obtenerUsuario(usuarioId)
      .then(({ data }) => {
        if (!activo) return
        const perfil = data.perfil ?? {}
        setForm({
          nombres: perfil.nombres ?? '',
          apellidos: perfil.apellidos ?? '',
          email: perfil.email ?? '',
          telefono: perfil.telefono ?? '',
          estado: perfil.estado ?? true,
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

  // Maneja tanto inputs de texto (usan e.target.value) como el
  // checkbox de "estado" (usa e.target.checked) — antes el checkbox
  // pasaba por acá con e.target.value ("on"/"" como string) en vez
  // de un booleano real.
  const handleChange = useCallback((e) => {
    const { name, type, value, checked } = e.target
    const nuevoValor = type === 'checkbox' ? checked : value
    setForm((prev) => ({ ...prev, [name]: nuevoValor }))
    setFieldErrors((prev) => (prev[name] ? { ...prev, [name]: null } : prev))
  }, [])

  const validar = () => {
    const errores = {}
    if (!form.nombres.trim()) errores.nombres = 'El nombre es obligatorio.'
    if (!form.apellidos.trim()) errores.apellidos = 'El apellido es obligatorio.'
    if (!form.email.trim()) errores.email = 'El correo es obligatorio.'
    else if (!/^\S+@\S+\.\S+$/.test(form.email)) errores.email = 'Correo inválido.'
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
      await usuariosApi.actualizarPerfil(usuarioId, {
        nombres: form.nombres.trim(),
        apellidos: form.apellidos.trim(),
        email: form.email.trim(),
        telefono: form.telefono.trim(),
        estado: form.estado,
      })
      setGuardado(true)
      return true
    } catch (err) {
      setFieldErrors(err.response?.data ?? {})
      setError(extraerMensajeError(err))
      return false
    } finally {
      setEnviando(false)
    }
  }

  return { form, fieldErrors, cargando, enviando, error, guardado, handleChange, submit }
}