// modules/casos/hooks/useCrearCaso.js
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import casosApi from '../../../api/casosApi'
import clientesApi from '../../../api/clientesApi'

const initialForm = {
  titulo: '',
  descripcion: '',
}

const initialClienteForm = {
  nombres: '',
  apellidos: '',
  telefono: '',
}

function validate(form, clienteForm, modo, archivo) {
  const errors = {}

  // Datos del caso
  if (!form.titulo.trim()) errors.titulo = 'El título es obligatorio.'
  if (modo === 'texto' && !form.descripcion.trim()) {
    errors.descripcion = 'Describe el caso o cambia a modo PDF.'
  }
  if (modo === 'pdf' && !archivo) {
    errors.archivo = 'Adjunta un archivo PDF.'
  }

  // Datos del cliente
  if (!clienteForm.nombres.trim()) errors.nombres = 'Los nombres son obligatorios.'
  if (!clienteForm.apellidos.trim()) errors.apellidos = 'Los apellidos son obligatorios.'
  if (!clienteForm.telefono.trim()) errors.telefono = 'El teléfono es obligatorio.'

  return errors
}

export default function useCrearCaso() {
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [clienteForm, setClienteForm] = useState(initialClienteForm)
  const [modo, setModo] = useState('texto') // 'texto' | 'pdf'
  const [archivo, setArchivo] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)

  const camposCliente = ['nombres', 'apellidos', 'email', 'telefono']

  const onChange = (e) => {
    const { name, value } = e.target

    if (camposCliente.includes(name)) {
      setClienteForm((prev) => ({ ...prev, [name]: value }))
    } else {
      setForm((prev) => ({ ...prev, [name]: value }))
    }

    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: undefined }))
    }
  }

  const onArchivoChange = (file) => {
    setArchivo(file)
    if (fieldErrors.archivo) {
      setFieldErrors((prev) => ({ ...prev, archivo: undefined }))
    }
  }

  const cambiarModo = (nuevoModo) => {
    setModo(nuevoModo)
    setFieldErrors({})
  }

  const onSubmit = async (e) => {
    e.preventDefault()
    const errors = validate(form, clienteForm, modo, archivo)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setEnviando(true)
    setError(null)

    try {
      // 1) Crear el cliente primero
      let cliente
      try {
        const res = await clientesApi.crear(clienteForm)
        cliente = res.data
        console.log('cliente creado:', cliente)  // ← agregá esto
      } catch (e) {
        console.error('Error creando cliente:', e, e?.response?.data)
        const apiErrors = e?.response?.data
        if (apiErrors && typeof apiErrors === 'object') {
          setFieldErrors(apiErrors)
        } else {
          setError('No se pudo crear el cliente.')
        }
        return
      }

      // 2) Crear el caso usando el id del cliente recién creado
      let data
      let config = {}

      if (modo === 'pdf') {
        data = new FormData()
        data.append('titulo', form.titulo)
        data.append('descripcion', form.descripcion || '')
        data.append('cliente_id', cliente.id)
        data.append('archivo_pdf', archivo)
        config = { headers: { 'Content-Type': 'multipart/form-data' } }
      } else {
        data = {
          titulo: form.titulo,
          descripcion: form.descripcion,
          cliente_id: cliente.id,
        }
      }

      const { data: caso } = await casosApi.crear(data, config)
      navigate(`/casos/${caso.id}`)
      return caso
    } catch (e) {
      console.error('Error creando caso:', e, e?.response?.data)
      const apiErrors = e?.response?.data
      if (apiErrors && typeof apiErrors === 'object') {
        setFieldErrors(apiErrors)
      } else {
        setError('No se pudo crear el caso.')
      }
    } finally {
      setEnviando(false)
    }
  }

  return {
    form,
    clienteForm,
    modo,
    archivo,
    fieldErrors,
    enviando,
    error,
    onChange,
    onArchivoChange,
    cambiarModo,
    onSubmit,
  }
}