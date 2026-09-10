// modules/clientes/hooks/useEditarCliente.js
import { useCallback, useEffect, useState } from 'react'
import clientesApi from '../../../api/clientesApi'

const initialForm = {
  nombres: '',
  apellidos: '',
  telefono: '',
}

function validate(form) {
  const errors = {}
  if (!form.nombres.trim()) errors.nombres = 'El nombre es obligatorio.'
  if (!form.apellidos.trim()) errors.apellidos = 'El apellido es obligatorio.'
  if (form.telefono) {
    if (form.telefono.length !== 8) {
      errors.telefono = 'El teléfono debe tener 8 dígitos.'
    } else if (!/^[67]/.test(form.telefono)) {
      errors.telefono = 'El teléfono debe empezar con 6 o 7.'
    }
  }
  return errors
}

export default function useEditarCliente(id) {
  const [clienteOriginal, setClienteOriginal] = useState(null)
  const [form, setForm] = useState(initialForm)
  const [fieldErrors, setFieldErrors] = useState({})
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const [guardadoOk, setGuardadoOk] = useState(false)

  const load = useCallback(async () => {
    setCargando(true)
    setError(null)
    try {
      const { data } = await clientesApi.obtener(id)
      setClienteOriginal(data)
      setForm({
        nombres: data.nombres ?? '',
        apellidos: data.apellidos ?? '',
        telefono: data.telefono ?? '',
      })
    } catch (e) {
      console.error('Error cargando cliente:', e, e?.response?.data)
      setError('No se pudo cargar el cliente.')
    } finally {
      setCargando(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  const onChange = (e) => {
    const { name, value } = e.target
    setGuardadoOk(false)
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
      const { data } = await clientesApi.actualizar(id, form)
      setClienteOriginal(data)
      setGuardadoOk(true)
      return data
    } catch (e) {
      console.error('Error actualizando cliente:', e, e?.response?.data)
      const apiErrors = e?.response?.data
      if (apiErrors && typeof apiErrors === 'object') {
        setFieldErrors(apiErrors)
      } else {
        setError('No se pudo guardar los cambios.')
      }
      throw e
    } finally {
      setEnviando(false)
    }
  }

  return {
    cliente: clienteOriginal,
    form,
    fieldErrors,
    cargando,
    error,
    enviando,
    guardadoOk,
    onChange,
    onSubmit,
    reload: load,
  }
}
