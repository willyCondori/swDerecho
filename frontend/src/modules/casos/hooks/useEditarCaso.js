// modules/casos/hooks/useEditarCaso.js
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import casosApi from '../../../api/casosApi'

const TITULO_MIN = 5
const TITULO_MAX = 500
const DESCRIPCION_MIN = 5

// Mismas reglas que CasoTituloDescripcionMixin en el backend
// (modulo_casos/serializers/caso_serializer.py), para que el usuario
// vea el error antes de mandar el request en vez de descubrirlo recién
// con la respuesta 400 del PATCH.
function validate(form) {
  const errors = {}

  const titulo = form.titulo.trim()
  if (!titulo) {
    errors.titulo = 'El título es obligatorio.'
  } else if (titulo.length < TITULO_MIN) {
    errors.titulo = `El título debe tener al menos ${TITULO_MIN} caracteres.`
  } else if (titulo.length > TITULO_MAX) {
    errors.titulo = `El título no puede exceder ${TITULO_MAX} caracteres.`
  }

  const descripcion = form.descripcion.trim()
  if (descripcion && descripcion.length < DESCRIPCION_MIN) {
    errors.descripcion = `La descripción debe tener al menos ${DESCRIPCION_MIN} caracteres.`
  }

  return errors
}

export default function useEditarCaso(id) {
  const navigate = useNavigate()

  const [form, setForm] = useState({ titulo: '', descripcion: '', estado: true })
  const [fieldErrors, setFieldErrors] = useState({})
  const [loading, setLoading] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState(null)

  // Datos de solo lectura del caso (código, cliente, etc.) para mostrar
  // de contexto en la pantalla, aunque no sean editables acá.
  const [casoOriginal, setCasoOriginal] = useState(null)

  const cargar = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await casosApi.obtener(id)
      setCasoOriginal(data)
      setForm({
        titulo: data.titulo ?? '',
        descripcion: data.descripcion ?? '',
        estado: data.estado ?? true,
      })
    } catch (e) {
      console.error('Error cargando caso para editar:', e, e?.response?.data)
      setError('No se pudo cargar el caso.')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    cargar()
  }, [cargar])

  const onChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
    if (fieldErrors[name]) setFieldErrors((prev) => ({ ...prev, [name]: null }))
  }

  const onSubmit = async (e) => {
    e.preventDefault()
    const errores = validate(form)
    if (Object.keys(errores).length) {
      setFieldErrors(errores)
      return
    }

    setGuardando(true)
    setError(null)
    try {
      await casosApi.actualizar(id, {
        titulo: form.titulo.trim(),
        descripcion: form.descripcion.trim() || null,
        estado: form.estado,
      })
      navigate(`/casos/${id}`)
    } catch (e) {
      console.error('Error guardando caso:', e, e?.response?.data)
      const data = e?.response?.data
      if (data && typeof data === 'object') {
        // DRF devuelve {campo: [mensajes]} en errores de validación
        const backendErrors = {}
        for (const [campo, mensajes] of Object.entries(data)) {
          backendErrors[campo] = Array.isArray(mensajes) ? mensajes[0] : String(mensajes)
        }
        setFieldErrors(backendErrors)
      }
      setError('No se pudieron guardar los cambios.')
    } finally {
      setGuardando(false)
    }
  }

  return {
    form,
    fieldErrors,
    loading,
    guardando,
    error,
    casoOriginal,
    onChange,
    onSubmit,
  }
}