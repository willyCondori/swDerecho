// modules/casos/hooks/useCrearCaso.js
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import casosApi from '../../../api/casosApi'
import clientesApi from '../../../api/clientesApi'

const initialForm = {
  titulo: '',
  descripcion: '',
  rama_id: '',
}

const initialClienteForm = {
  nombres: '',
  apellidos: '',
  telefono: '',
}

function validate(form, clienteForm, modo, archivo, modoCliente, clienteExistenteId) {
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
  if (modoCliente === 'nuevo') {
    if (!clienteForm.nombres.trim()) errors.nombres = 'Los nombres son obligatorios.'
    if (!clienteForm.apellidos.trim()) errors.apellidos = 'Los apellidos son obligatorios.'
    if (!clienteForm.telefono.trim()) errors.telefono = 'El teléfono es obligatorio.'
  } else {
    if (!clienteExistenteId) errors.clienteExistente = 'Selecciona un cliente existente.'
  }

  return errors
}

export default function useCrearCaso() {
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [clienteForm, setClienteForm] = useState(initialClienteForm)
  const [modoCliente, setModoCliente] = useState('nuevo') // 'nuevo' | 'existente'
  const [clienteExistenteId, setClienteExistenteId] = useState(null)
  const [clienteExistenteNombre, setClienteExistenteNombre] = useState('')
  const [modo, setModo] = useState('texto') // 'texto' | 'pdf'
  const [archivo, setArchivo] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)

  const camposCliente = ['nombres', 'apellidos', 'telefono']

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

  const cambiarModoCliente = (nuevoModoCliente) => {
    setModoCliente(nuevoModoCliente)
    setClienteExistenteId(null)
    setClienteExistenteNombre('')
    setFieldErrors({})
  }

  const seleccionarClienteExistente = (id, nombre) => {
    setClienteExistenteId(id)
    setClienteExistenteNombre(nombre)
    if (fieldErrors.clienteExistente) {
      setFieldErrors((prev) => ({ ...prev, clienteExistente: undefined }))
    }
  }

  const onSubmit = async (e) => {
    e.preventDefault()
    const errors = validate(form, clienteForm, modo, archivo, modoCliente, clienteExistenteId)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setEnviando(true)
    setError(null)

    try {
      let clienteId

      if (modoCliente === 'nuevo') {
        // 1) Crear el cliente primero
        try {
          const res = await clientesApi.crear(clienteForm)
          clienteId = res.data.id
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
      } else {
        // Cliente ya existente, seleccionado del buscador
        clienteId = clienteExistenteId
      }

      // 2) Crear el caso usando el id del cliente (nuevo o existente)
      let data
      let config = {}

      if (modo === 'pdf') {
        data = new FormData()
        data.append('titulo', form.titulo)
        data.append('descripcion', form.descripcion || '')
        data.append('cliente_id', clienteId)
        data.append('archivo_pdf', archivo)
        if (form.rama_id) data.append('rama_detectada_id', form.rama_id)
        config = { headers: { 'Content-Type': 'multipart/form-data' } }
      } else {
        data = {
          titulo: form.titulo,
          descripcion: form.descripcion,
          cliente_id: clienteId,
          ...(form.rama_id ? { rama_detectada_id: form.rama_id } : {}),
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
    modoCliente,
    clienteExistenteId,
    clienteExistenteNombre,
    onChange,
    onArchivoChange,
    cambiarModo,
    cambiarModoCliente,
    seleccionarClienteExistente,
    onSubmit,
  }
}