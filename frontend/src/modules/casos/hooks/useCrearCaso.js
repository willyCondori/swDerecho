// modules/casos/hooks/useCrearCaso.js
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import casosApi from '../../../api/casosApi'
import { tieneEspaciosExcesivos, tieneEmoji } from '../../../utils/validators'

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

const NOMBRE_REGEX = /^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$/

function validate(form, clienteForm, modo, archivo, modoCliente, clienteExistenteId) {
  const errors = {}

  // Datos del caso
  if (!form.titulo.trim()) {
    errors.titulo = 'El título es obligatorio.'
  } else if (tieneEmoji(form.titulo)) {
    errors.titulo = 'El título no puede contener emojis.'
  } else if (tieneEspaciosExcesivos(form.titulo)) {
    errors.titulo = 'El título no puede tener más de 2 espacios seguidos.'
  }
  if (!form.rama_id) {
    errors.rama_id = 'Selecciona la rama del derecho del caso (penal, civil, u otra).'
  }
  if (modo === 'texto' && !form.descripcion.trim()) {
    errors.descripcion = 'Describe el caso o cambia a modo PDF.'
  }
  if (modo === 'pdf' && !archivo) {
    errors.archivo = 'Adjunta un archivo PDF.'
  }

  // Datos del cliente — mismas reglas que valida el backend
  // (ClienteWriteSerializer), para no depender del round-trip al
  // servidor para avisar de un dato inválido.
  if (modoCliente === 'nuevo') {
    const nombres = clienteForm.nombres.trim()
    const apellidos = clienteForm.apellidos.trim()
    const telefono = clienteForm.telefono.trim()

    if (!nombres) {
      errors.nombres = 'Los nombres son obligatorios.'
    } else if (nombres.length < 2) {
      errors.nombres = 'El nombre debe tener al menos 2 caracteres.'
    } else if (!NOMBRE_REGEX.test(nombres)) {
      errors.nombres = 'El nombre solo puede contener letras y espacios.'
    } else if (tieneEspaciosExcesivos(clienteForm.nombres)) {
      errors.nombres = 'El nombre no puede tener más de 2 espacios seguidos.'
    }

    if (!apellidos) {
      errors.apellidos = 'Los apellidos son obligatorios.'
    } else if (apellidos.length < 2) {
      errors.apellidos = 'Los apellidos deben tener al menos 2 caracteres.'
    } else if (!NOMBRE_REGEX.test(apellidos)) {
      errors.apellidos = 'Los apellidos solo pueden contener letras y espacios.'
    } else if (tieneEspaciosExcesivos(clienteForm.apellidos)) {
      errors.apellidos = 'Los apellidos no pueden tener más de 2 espacios seguidos.'
    }

    if (!telefono) {
      errors.telefono = 'El teléfono es obligatorio.'
    } else if (telefono.length !== 8 || !/^\d+$/.test(telefono)) {
      errors.telefono = 'El teléfono debe tener 8 dígitos.'
    } else if (!/^[67]/.test(telefono)) {
      errors.telefono = 'El teléfono debe empezar con 6 o 7.'
    }
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
      // Cliente nuevo y caso se guardan juntos en el backend. Una segunda
      // petición dejaría al cliente creado si el caso fuera rechazado.
      const datos = {
        titulo: form.titulo,
        descripcion: form.descripcion || '',
        rama_detectada_id: form.rama_id,
        ...(modoCliente === 'nuevo' ? clienteForm : { cliente_id: clienteExistenteId }),
      }
      let data = datos
      let config = {}

      if (modo === 'pdf') {
        data = new FormData()
        for (const [campo, valor] of Object.entries(datos)) {
          data.append(campo, valor)
        }
        data.append('archivo_pdf', archivo)
        config = { headers: { 'Content-Type': 'multipart/form-data' } }
      }

      const { data: caso } = modoCliente === 'nuevo'
        ? await casosApi.crearConCliente(data, config)
        : await casosApi.crear(data, config)
      navigate(`/casos/${caso.id}`)
      return caso
    } catch (e) {
      console.error('Error creando caso:', e, e?.response?.data)
      const apiErrors = e?.response?.data
      if (apiErrors && typeof apiErrors === 'object' && !Array.isArray(apiErrors)) {
        setFieldErrors({
          ...apiErrors,
          rama_id: apiErrors.rama_detectada_id,
          archivo: apiErrors.archivo_pdf ?? apiErrors.archivo,
        })
        const mensaje = apiErrors.non_field_errors ?? apiErrors.detail
        if (mensaje) setError(Array.isArray(mensaje) ? mensaje.join(' ') : mensaje)
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
