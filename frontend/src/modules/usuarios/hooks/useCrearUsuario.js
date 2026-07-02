// modules/usuarios/hooks/useCrearUsuario.js
import { useState } from 'react'
import usuariosService from '../services/usuariosService'

const FORM_INICIAL = {
  usuario: '',
  password: '',
  confirmarPassword: '',
  rolId: '',
  estado: true,
}

function extraerMensajeError(err) {
  const data = err.response?.data
  if (!data) return 'No se pudo crear el usuario.'
  if (typeof data.detail === 'string') return data.detail
  const primerCampo = Object.values(data)[0]
  if (Array.isArray(primerCampo)) return primerCampo[0]
  return 'No se pudo crear el usuario.'
}

/**
 * Maneja el formulario de alta de usuario: estado de campos,
 * validación y llamada a POST /api/usuarios/.
 */
export function useCrearUsuario() {
  const [form, setForm] = useState(FORM_INICIAL)
  const [fieldErrors, setFieldErrors] = useState({})
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)
  const [creado, setCreado] = useState(null)

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
    if (fieldErrors[name]) setFieldErrors((prev) => ({ ...prev, [name]: null }))
  }

  const validar = () => {
    const errores = {}
    if (!form.usuario.trim()) errores.usuario = 'El nombre de usuario es obligatorio.'
    if (!form.password) errores.password = 'La contraseña es obligatoria.'
    else if (form.password.length < 8) errores.password = 'Debe tener al menos 8 caracteres.'
    if (form.password !== form.confirmarPassword) {
      errores.confirmarPassword = 'Las contraseñas no coinciden.'
    }
    if (!form.rolId) errores.rolId = 'Selecciona un rol.'
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
    try {
      const { data } = await usuariosService.crear({
        usuario: form.usuario.trim(),
        password: form.password,
        rol: form.rolId,
        estado: form.estado,
      })
      setCreado(data)
      return true
    } catch (err) {
      setError(extraerMensajeError(err))
      return false
    } finally {
      setEnviando(false)
    }
  }

  const reset = () => {
    setForm(FORM_INICIAL)
    setFieldErrors({})
    setError(null)
    setCreado(null)
  }

  return { form, fieldErrors, enviando, error, creado, handleChange, submit, reset }
}