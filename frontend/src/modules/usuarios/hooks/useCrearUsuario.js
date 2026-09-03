import { useState } from 'react'
import usuariosApi from '../../../api/usuariosApi'

const FORM_INICIAL = {
  usuario: '',
  rolId: '',
  estado: true,

  perfil: {
    nombres: '',
    apellidos: '',
    email: '',
    telefono: '',
  },
}

function extraerMensajeError(err) {
  const data = err.response?.data
  if (!data) return 'No se pudo crear el usuario.'
  if (typeof data.detail === 'string') return data.detail

  const primerCampo = Object.values(data)[0]
  if (Array.isArray(primerCampo)) return primerCampo[0]

  return 'No se pudo crear el usuario.'
}

export function useCrearUsuario() {
  const [form, setForm] = useState(FORM_INICIAL)
  const [fieldErrors, setFieldErrors] = useState({})
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)
  const [creado, setCreado] = useState(null)

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target

    // 👇 PERFIL
    if (name in form.perfil) {
      setForm((prev) => ({
        ...prev,
        perfil: {
          ...prev.perfil,
          [name]: value,
        },
      }))
    } else {
      setForm((prev) => ({
        ...prev,
        [name]: type === 'checkbox' ? checked : value,
      }))
    }

    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: null }))
    }
  }

  const validar = () => {
    const errores = {}
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    const phoneRegex = /^[67]\d{7}$/

    if (!form.usuario.trim()) errores.usuario = 'Usuario requerido'
    if (!form.rolId) errores.rolId = 'Selecciona un rol.'

    // 👇 PERFIL VALIDACIÓN BÁSICA
    if (!form.perfil.nombres.trim()) errores.nombres = 'Nombre requerido'
    if (!form.perfil.apellidos.trim()) errores.apellidos = 'Apellido requerido'
    if (!form.perfil.email.trim()) {
      errores.email = 'Email requerido'
    } else if (!emailRegex.test(form.perfil.email)) {
      errores.email = 'Email inválido'
    }

    if (!form.perfil.telefono) {
      errores.telefono = 'Teléfono requerido'
    } else if (!phoneRegex.test(form.perfil.telefono)) {
      errores.telefono = 'Teléfono inválido (8 dígitos, inicia 6/7)'
    }
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
      const { data } = await usuariosApi.crearUsuario({
        usuario: form.usuario.trim(),
        rol_id: form.rolId,
        estado: form.estado,
        perfil: form.perfil,
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