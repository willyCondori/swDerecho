// modules/usuarios/hooks/useEditarUsuario.js
import { useCallback, useEffect, useState } from 'react'
import usuariosApi from '../../../api/usuariosApi'

const PERFIL_FIELDS = ['nombres', 'apellidos', 'email', 'telefono']

const initialForm = {
  usuario: '',
  cambiarPassword: false,
  password: '',
  confirmarPassword: '',
  rolId: '',
  estado: true,
  perfil: {
    nombres: '',
    apellidos: '',
    email: '',
    telefono: '',
  },
}

function validate(form) {
  const errors = {}

  if (!form.rolId) errors.rolId = 'Selecciona un rol.'
  if (!form.perfil.nombres.trim()) errors.nombres = 'El nombre es obligatorio.'
  if (!form.perfil.apellidos.trim()) errors.apellidos = 'El apellido es obligatorio.'
  if (form.perfil.email && !/^\S+@\S+\.\S+$/.test(form.perfil.email)) {
    errors.email = 'Correo inválido.'
  }
  if (form.perfil.telefono && form.perfil.telefono.length < 7) {
    errors.telefono = 'Teléfono incompleto.'
  }

  if (form.cambiarPassword) {
    if (!form.password) errors.password = 'Ingresa la nueva contraseña.'
    if (form.password && form.password.length < 8) {
      errors.password = 'Debe tener al menos 8 caracteres.'
    }
    if (form.password !== form.confirmarPassword) {
      errors.confirmarPassword = 'Las contraseñas no coinciden.'
    }
  }

  return errors
}

export default function useEditarUsuario(id) {
  const [usuarioOriginal, setUsuarioOriginal] = useState(null)
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
      const { data } = await usuariosApi.obtenerUsuario(id)
      setUsuarioOriginal(data)
      setForm({
        usuario: data.usuario ?? '',
        cambiarPassword: false,
        password: '',
        confirmarPassword: '',
        rolId: data.rol?.id ?? data.rol ?? '',
        estado: Boolean(data.estado),
        perfil: {
          nombres: data.perfil?.nombres ?? '',
          apellidos: data.perfil?.apellidos ?? '',
          email: data.perfil?.email ?? '',
          telefono: data.perfil?.telefono ?? '',
        },
      })
    } catch (e) {
      console.error('Error cargando usuario:', e, e?.response?.data)
      setError('No se pudo cargar el usuario.')
    } finally {
      setCargando(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  const onChange = (e) => {
    const { name, value, type, checked } = e.target
    setGuardadoOk(false)

    setForm((prev) => {
      if (type === 'checkbox') {
        return { ...prev, [name]: checked }
      }
      if (PERFIL_FIELDS.includes(name)) {
        return { ...prev, perfil: { ...prev.perfil, [name]: value } }
      }
      return { ...prev, [name]: value }
    })

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
      // El backend separa "datos de cuenta" (rol, estado, password) de "perfil"
      // (nombres, apellidos, email, telefono) en dos endpoints distintos.
      const usuarioPayload = {
        rol: form.rolId,
        estado: form.estado,
      }
      if (form.cambiarPassword && form.password) {
        usuarioPayload.password = form.password
      }

      const [usuarioRes, perfilRes] = await Promise.all([
        usuariosApi.actualizarUsuario(id, usuarioPayload),
        usuariosApi.actualizarPerfil(id, { ...form.perfil }),
      ])

      setUsuarioOriginal({ ...usuarioRes.data, perfil: perfilRes.data })
      setGuardadoOk(true)
      return usuarioRes.data
    } catch (e) {
      console.error('Error guardando usuario:', e, e?.response?.data)
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
    usuario: usuarioOriginal,
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