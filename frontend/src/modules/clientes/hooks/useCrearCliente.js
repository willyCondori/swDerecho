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

function validate(form) {
  const errors = {}
  if (!form.nombres.trim()) errors.nombres = 'El nombre es obligatorio.'
  if (!form.apellidos.trim()) errors.apellidos = 'El apellido es obligatorio.'
  if (form.email && !/^\S+@\S+\.\S+$/.test(form.email)) errors.email = 'Correo inválido.'
  if (form.telefono && form.telefono.length < 7) errors.telefono = 'Teléfono incompleto.'
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