// modules/usuarios/pages/RolesPage.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useGestionRoles from '../hooks/useGestionRoles'
import RolTable from '../components/RolTable'
import RolForm from '../components/RolForm'
import styles from './RolesPage.module.css'

const TABS = [
  { value: 'activos', label: 'Activos' },
  { value: 'eliminados', label: 'Eliminados' },
]

const FORM_VACIO = { nombre: '', descripcion: '' }

function extraerErroresCampo(err) {
  const data = err.response?.data
  if (!data) return { detail: 'No se pudo guardar el rol.' }
  if (typeof data.detail === 'string') return { detail: data.detail }

  const errores = {}
  for (const [campo, mensajes] of Object.entries(data)) {
    errores[campo] = Array.isArray(mensajes) ? mensajes[0] : String(mensajes)
  }
  return errores
}

export default function RolesPage() {
  const navigate = useNavigate()
  const {
    roles,
    loading,
    error,
    count,
    search,
    setSearch,
    estadoFiltro,
    setEstadoFiltro,
    reload,
    crearRol,
    actualizarRol,
    eliminarRol,
    activarRol,
  } = useGestionRoles()

  // 'cerrado' | 'crear' | { editar: rol }
  const [panel, setPanel] = useState('cerrado')
  const [form, setForm] = useState(FORM_VACIO)
  const [fieldErrors, setFieldErrors] = useState({})
  const [enviando, setEnviando] = useState(false)

  const abrirCrear = () => {
    setForm(FORM_VACIO)
    setFieldErrors({})
    setPanel('crear')
  }

  const abrirEditar = (rol) => {
    setForm({ nombre: rol.nombre, descripcion: rol.descripcion || '' })
    setFieldErrors({})
    setPanel({ editar: rol })
  }

  const cerrarPanel = () => {
    setPanel('cerrado')
    setForm(FORM_VACIO)
    setFieldErrors({})
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: null }))
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setEnviando(true)
    setFieldErrors({})
    try {
      if (panel === 'crear') {
        await crearRol(form)
      } else if (panel && panel.editar) {
        await actualizarRol(panel.editar.id, form)
      }
      cerrarPanel()
    } catch (err) {
      setFieldErrors(extraerErroresCampo(err))
    } finally {
      setEnviando(false)
    }
  }

  const handleEliminar = async (rol) => {
    if (!window.confirm(`¿Desactivar el rol "${rol.nombre}"? Podrás recuperarlo luego desde la pestaña "Eliminados".`)) return
    try {
      await eliminarRol(rol.id)
    } catch (e) {
      window.alert(e?.response?.data?.detail || 'No se pudo desactivar el rol.')
    }
  }

  const handleRecuperar = async (rol) => {
    if (!window.confirm(`¿Reactivar el rol "${rol.nombre}"? Volverá a estar disponible para asignar a usuarios.`)) return
    try {
      await activarRol(rol.id)
    } catch (e) {
      window.alert(e?.response?.data?.detail || 'No se pudo reactivar el rol.')
    }
  }

  return (
    <div className={styles.root}>
      {/* ── Encabezado ─────────────────────────── */}
      <div className={styles.headerRow}>
        <button
          type="button"
          className={styles.backBtn}
          onClick={() => navigate('/usuarios')}
          aria-label="Volver a usuarios"
        >
          <i className="ti ti-arrow-left" aria-hidden="true" />
        </button>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Roles</h1>
            <p className={styles.subtitle}>
              Define los roles disponibles y el nivel de acceso que otorgan a los usuarios del sistema.
            </p>
          </div>
          <div className={styles.headerActions}>
            {panel === 'cerrado' && (
              <button className={styles.btnPrimary} onClick={abrirCrear}>
                <i className="ti ti-shield-plus" aria-hidden="true" />
                Nuevo rol
              </button>
            )}
          </div>
        </header>
      </div>

      {/* ── Panel de creación/edición ──────────────────── */}
      {panel !== 'cerrado' && (
        <RolForm
          mode={panel === 'crear' ? 'crear' : 'editar'}
          form={form}
          fieldErrors={fieldErrors}
          enviando={enviando}
          onChange={handleChange}
          onSubmit={handleSubmit}
          onCancel={cerrarPanel}
        />
      )}

      {/* ── Toolbar ────────────────────────────── */}
      <div className={styles.toolbar}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3, 16px)', flexWrap: 'wrap' }}>
          <div className={styles.tabs}>
            {TABS.map((tab) => (
              <button
                key={tab.value}
                className={`${styles.tab} ${estadoFiltro === tab.value ? styles.tabActive : ''}`}
                onClick={() => setEstadoFiltro(tab.value)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className={styles.searchBox}>
            <i className={`ti ti-search ${styles.searchIcon}`} aria-hidden="true" />
            <input
              type="text"
              className={styles.searchInput}
              placeholder="Buscar por nombre o descripción..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {!loading && !error && (
          <span className={styles.resultCount}>
            {count} {count === 1 ? 'rol' : 'roles'}
          </span>
        )}
      </div>

      {/* ── Tabla ──────────────────────────────── */}
      <div className={styles.card}>
        <RolTable
          roles={roles}
          loading={loading}
          error={error}
          onRetry={reload}
          onEditar={abrirEditar}
          onEliminar={handleEliminar}
          onRecuperar={handleRecuperar}
          onCrearPrimero={abrirCrear}
        />
      </div>
    </div>
  )
}
