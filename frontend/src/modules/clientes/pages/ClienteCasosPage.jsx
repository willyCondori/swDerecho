// modules/clientes/pages/ClienteCasosPage.jsx
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import useClienteCasos from '../hooks/useClienteCasos'
import useAuthStore from '../../auth/store/authStore'
import clientesApi from '../../../api/clientesApi'
import ClienteForm from '../components/ClienteForm'
import styles from './ClienteCasosPage.module.css'

function getNombreCompleto(cliente) {
  if (!cliente) return ''
  const nombres = cliente.nombres ?? ''
  const apellidos = cliente.apellidos ?? ''
  return `${nombres} ${apellidos}`.trim() || `Cliente #${cliente.id}`
}

function EstadoBadge({ caso }) {
  if (caso.tiene_resultado) {
    return <span className={`${styles.badge} ${styles.badgeOk}`}>Análisis completo</span>
  }
  if (caso.tiene_documento) {
    return <span className={`${styles.badge} ${styles.badgePending}`}>PDF adjunto</span>
  }
  return <span className={`${styles.badge} ${styles.badgeMuted}`}>Sin analizar</span>
}

function validarCliente(form) {
  const errors = {}
  const nombres = form.nombres.trim()
  const apellidos = form.apellidos.trim()
  const telefono = form.telefono.trim()

  const soloLetras = /^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$/

  if (!nombres) {
    errors.nombres = 'El nombre es obligatorio.'
  } else if (nombres.length < 2) {
    errors.nombres = 'El nombre debe tener al menos 2 caracteres.'
  } else if (!soloLetras.test(nombres)) {
    errors.nombres = 'El nombre solo puede contener letras y espacios.'
  }

  if (!apellidos) {
    errors.apellidos = 'Los apellidos son obligatorios.'
  } else if (apellidos.length < 2) {
    errors.apellidos = 'Los apellidos deben tener al menos 2 caracteres.'
  } else if (!soloLetras.test(apellidos)) {
    errors.apellidos = 'Los apellidos solo pueden contener letras y espacios.'
  }

  if (telefono) {
    if (telefono.length !== 8 || !/^\d+$/.test(telefono)) {
      errors.telefono = 'El teléfono debe tener 8 dígitos.'
    } else if (!/^[67]/.test(telefono)) {
      errors.telefono = 'El teléfono debe empezar con 6 o 7.'
    }
  }

  return errors
}

export default function ClienteCasosPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const puedeEscribir = useAuthStore((s) => s.puedeEscribir())
  const { cliente, casos, loading, error, reload } = useClienteCasos(id)

  const [editando, setEditando] = useState(false)
  const [form, setForm] = useState({ nombres: '', apellidos: '', telefono: '' })
  const [fieldErrors, setFieldErrors] = useState({})
  const [enviando, setEnviando] = useState(false)

  const abrirEdicion = () => {
    setForm({
      nombres: cliente.nombres || '',
      apellidos: cliente.apellidos || '',
      telefono: cliente.telefono || '',
    })
    setFieldErrors({})
    setEditando(true)
  }

  const cerrarEdicion = () => {
    setEditando(false)
    setFieldErrors({})
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    if (fieldErrors[name]) setFieldErrors((prev) => ({ ...prev, [name]: undefined }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errors = validarCliente(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setEnviando(true)
    try {
      await clientesApi.actualizar(id, form)
      await reload()
      cerrarEdicion()
    } catch (e) {
      console.error('Error actualizando cliente:', e, e?.response?.data)
      const apiErrors = e?.response?.data
      if (apiErrors && typeof apiErrors === 'object') {
        setFieldErrors(apiErrors)
      } else {
        window.alert('No se pudo actualizar el cliente.')
      }
    } finally {
      setEnviando(false)
    }
  }

  if (loading) {
    return <div className={styles.loaderWrap}>Cargando cliente...</div>
  }

  if (error && !cliente) {
    return (
      <div className={styles.root}>
        <div className={styles.errorBanner}>{error}</div>
        <button className={styles.btnSecondary} onClick={() => navigate('/clientes')}>
          Volver a clientes
        </button>
      </div>
    )
  }

  if (!cliente) return null

  return (
    <div className={styles.root}>
      <div className={styles.headerRow}>
        <button type="button" className={styles.backBtn} onClick={() => navigate('/clientes')} aria-label="Volver">
          <i className="ti ti-arrow-left" aria-hidden="true" />
        </button>
        <div className={styles.headerInfo}>
          <h1 className={styles.title}>{getNombreCompleto(cliente)}</h1>
          {cliente.telefono && <p className={styles.codigo}>{cliente.telefono}</p>}
        </div>
        <div className={styles.headerActions}>
          {puedeEscribir && !editando && (
            <button type="button" className={styles.btnPrimary} onClick={abrirEdicion}>
              <i className="ti ti-pencil" aria-hidden="true" />
              Editar datos
            </button>
          )}
        </div>
      </div>

      {error && <div className={styles.errorBanner}>{error}</div>}

      {puedeEscribir && editando && (
        <ClienteForm
          form={form}
          fieldErrors={fieldErrors}
          enviando={enviando}
          onChange={handleChange}
          onSubmit={handleSubmit}
          submitLabel={enviando ? 'Guardando...' : 'Guardar cambios'}
        />
      )}
      {puedeEscribir && editando && (
        <button type="button" className={styles.btnSecondary} onClick={cerrarEdicion} disabled={enviando}>
          Cancelar
        </button>
      )}

      <div className={styles.card}>
        <h2 className={styles.cardTitle}>
          <i className="ti ti-briefcase" aria-hidden="true" /> Casos del cliente
        </h2>

        {casos.length === 0 ? (
          <p className={styles.emptyText}>Este cliente todavía no tiene casos registrados.</p>
        ) : (
          <ol className={styles.list}>
            {casos.map((caso) => (
              <li
                key={caso.id}
                className={styles.listItem}
                onClick={() => navigate(`/casos/${caso.id}`)}
              >
                <div className={styles.codigoRow}>
                  <span className={styles.codigo}>{caso.codigo}</span>
                  <EstadoBadge caso={caso} />
                </div>
                <p className={styles.descripcion}>{caso.titulo}</p>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  )
}