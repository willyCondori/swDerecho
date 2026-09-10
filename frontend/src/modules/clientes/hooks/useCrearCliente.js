// modules/clientes/hooks/useCrearCliente.js
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import clientesApi from '../../../api/clientesApi'

const initialForm = {
  nombres: '',
  apellidos: '',
  email: '',
  telefono: '',
}

const NOMBRE_REGEX = /^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$/

function validate(form) {
  const errors = {}
  const nombres = form.nombres.trim()
  const apellidos = form.apellidos.trim()

  if (!nombres) {
    errors.nombres = 'El nombre es obligatorio.'
  } else if (nombres.length < 2) {
    errors.nombres = 'El nombre debe tener al menos 2 caracteres.'
  } else if (!NOMBRE_REGEX.test(nombres)) {
    errors.nombres = 'El nombre solo puede contener letras y espacios.'
  }

  if (!apellidos) {
    errors.apellidos = 'El apellido es obligatorio.'
  } else if (apellidos.length < 2) {
    errors.apellidos = 'El apellido debe tener al menos 2 caracteres.'
  } else if (!NOMBRE_REGEX.test(apellidos)) {
    errors.apellidos = 'El apellido solo puede contener letras y espacios.'
  }

  if (form.email && !/^\S+@\S+\.\S+$/.test(form.email)) errors.email = 'Correo inválido.'
  if (form.telefono) {
    if (form.telefono.length !== 8) {
      errors.telefono = 'El teléfono debe tener 8 dígitos.'
    } else if (!/^[67]/.test(form.telefono)) {
      errors.telefono = 'El teléfono debe empezar con 6 o 7.'
    }
  }
  return errors
}

export default function useCrearCliente() {
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [fieldErrors, setFieldErrors] = useState({})
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)

  const onChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: undefined }))
    }
  }

  const onSubmit = async (e) => {
    e.preventDefault()
    const errors = validate(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setEnviando(true)
    setError(null)
    try {
      const { data } = await clientesApi.crear(form)
      navigate('/clientes')
      return data
    } catch (e) {
      console.error('Error creando cliente:', e, e?.response?.data)
      const apiErrors = e?.response?.data
      if (apiErrors && typeof apiErrors === 'object') {
        setFieldErrors(apiErrors)
      } else {
        setError('No se pudo crear el cliente.')
      }
    } finally {
      setEnviando(false)
    }
  }

  return { form, fieldErrors, enviando, error, onChange, onSubmit }
}