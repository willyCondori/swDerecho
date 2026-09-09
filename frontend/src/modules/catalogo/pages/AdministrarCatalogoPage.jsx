// modules/catalogo/pages/AdministrarCatalogoPage.jsx
import { useState } from 'react'
import useGestionRamas from '../hooks/useGestionRamas'
import useGestionJerarquias from '../hooks/useGestionJerarquias'
import RamaForm from '../components/administrar/RamaForm'
import RamaTable from '../components/administrar/RamaTable'
import JerarquiaForm from '../components/administrar/JerarquiaForm'
import JerarquiaTable from '../components/administrar/JerarquiaTable'
import styles from './AdministrarCatalogoPage.module.css'

const TABS = [
  { value: 'ramas', label: 'Ramas de derecho', icon: 'ti-gavel' },
  { value: 'jerarquias', label: 'Jerarquías (tipos de norma)', icon: 'ti-stack-2' },
]

const FORM_RAMA_VACIO = { nombre: '', descripcion: '' }
const FORM_JERARQUIA_VACIO = { nombre: '', nivel: '' }

function extraerErroresCampo(err, mensajeDefault) {
  const data = err.response?.data
  if (!data) return { detail: mensajeDefault }
  if (typeof data.detail === 'string') return { detail: data.detail }

  const errores = {}
  for (const [campo, mensajes] of Object.entries(data)) {
    errores[campo] = Array.isArray(mensajes) ? mensajes[0] : String(mensajes)
  }
  return errores
}

export default function AdministrarCatalogoPage() {
  const [tab, setTab] = useState('ramas')

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Ramas y jerarquías</h1>
          <p className={styles.subtitle}>
            Administra las ramas de derecho y los tipos de norma (jerarquía)
            disponibles en el catálogo. Cualquiera que crees acá aparece de
            inmediato en el formulario de "Cargar artículos jurídicos".
          </p>
        </div>
      </header>

      <div className={styles.tabs}>
        {TABS.map((t) => (
          <button
            key={t.value}
            className={`${styles.tab} ${tab === t.value ? styles.tabActive : ''}`}
            onClick={() => setTab(t.value)}
            type="button"
          >
            <i className={`ti ${t.icon}`} aria-hidden="true" />
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'ramas' ? <RamasSection /> : <JerarquiasSection />}
    </div>
  )
}

function RamasSection() {
  const {
    ramas, loading, error, reload,
    crearRama, actualizarRama, eliminarRama,
  } = useGestionRamas()

  const [panel, setPanel] = useState('cerrado') // 'cerrado' | 'crear' | { editar: rama }
  const [form, setForm] = useState(FORM_RAMA_VACIO)
  const [fieldErrors, setFieldErrors] = useState({})
  const [enviando, setEnviando] = useState(false)

  const abrirCrear = () => {
    setForm(FORM_RAMA_VACIO)
    setFieldErrors({})
    setPanel('crear')
  }
  const abrirEditar = (rama) => {
    setForm({ nombre: rama.nombre, descripcion: rama.descripcion || '' })
    setFieldErrors({})
    setPanel({ editar: rama })
  }
  const cerrarPanel = () => {
    setPanel('cerrado')
    setForm(FORM_RAMA_VACIO)
    setFieldErrors({})
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    if (fieldErrors[name]) setFieldErrors((prev) => ({ ...prev, [name]: null }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setEnviando(true)
    setFieldErrors({})
    try {
      if (panel === 'crear') {
        await crearRama(form)
      } else if (panel && panel.editar) {
        await actualizarRama(panel.editar.id, form)
      }
      cerrarPanel()
    } catch (err) {
      setFieldErrors(extraerErroresCampo(err, 'No se pudo guardar la rama de derecho.'))
    } finally {
      setEnviando(false)
    }
  }

  const handleEliminar = async (rama) => {
    if (!window.confirm(`¿Eliminar la rama "${rama.nombre}"? Los artículos ya cargados con esta rama no se ven afectados, pero dejará de aparecer como opción al cargar nuevos documentos.`)) return
    try {
      await eliminarRama(rama.id)
    } catch (e) {
      window.alert(e?.response?.data?.detail || 'No se pudo eliminar la rama de derecho.')
    }
  }

  return (
    <>
      <div className={styles.sectionToolbar}>
        {panel === 'cerrado' && (
          <button className={styles.btnPrimary} onClick={abrirCrear}>
            <i className="ti ti-plus" aria-hidden="true" />
            Nueva rama de derecho
          </button>
        )}
      </div>

      {panel !== 'cerrado' && (
        <RamaForm
          mode={panel === 'crear' ? 'crear' : 'editar'}
          form={form}
          fieldErrors={fieldErrors}
          enviando={enviando}
          onChange={handleChange}
          onSubmit={handleSubmit}
          onCancel={cerrarPanel}
        />
      )}

      <div className={styles.card}>
        <RamaTable
          ramas={ramas}
          loading={loading}
          error={error}
          onRetry={reload}
          onEditar={abrirEditar}
          onEliminar={handleEliminar}
          onCrearPrimero={abrirCrear}
        />
      </div>
    </>
  )
}

function JerarquiasSection() {
  const {
    jerarquias, loading, error, reload,
    crearJerarquia, actualizarJerarquia, eliminarJerarquia,
  } = useGestionJerarquias()

  const [panel, setPanel] = useState('cerrado') // 'cerrado' | 'crear' | { editar: jerarquia }
  const [form, setForm] = useState(FORM_JERARQUIA_VACIO)
  const [fieldErrors, setFieldErrors] = useState({})
  const [enviando, setEnviando] = useState(false)

  const abrirCrear = () => {
    setForm(FORM_JERARQUIA_VACIO)
    setFieldErrors({})
    setPanel('crear')
  }
  const abrirEditar = (jerarquia) => {
    setForm({ nombre: jerarquia.nombre, nivel: String(jerarquia.nivel) })
    setFieldErrors({})
    setPanel({ editar: jerarquia })
  }
  const cerrarPanel = () => {
    setPanel('cerrado')
    setForm(FORM_JERARQUIA_VACIO)
    setFieldErrors({})
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    if (fieldErrors[name]) setFieldErrors((prev) => ({ ...prev, [name]: null }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setEnviando(true)
    setFieldErrors({})
    try {
      const payload = { nombre: form.nombre, nivel: Number(form.nivel) }
      if (panel === 'crear') {
        await crearJerarquia(payload)
      } else if (panel && panel.editar) {
        await actualizarJerarquia(panel.editar.id, payload)
      }
      cerrarPanel()
    } catch (err) {
      setFieldErrors(extraerErroresCampo(err, 'No se pudo guardar la jerarquía.'))
    } finally {
      setEnviando(false)
    }
  }

  const handleEliminar = async (jerarquia) => {
    if (!window.confirm(`¿Eliminar la jerarquía "${jerarquia.nombre}"? Las normas que ya la tienen asignada no se ven afectadas, pero dejará de aparecer como opción al cargar nuevos documentos.`)) return
    try {
      await eliminarJerarquia(jerarquia.id)
    } catch (e) {
      window.alert(e?.response?.data?.detail || 'No se pudo eliminar la jerarquía.')
    }
  }

  return (
    <>
      <div className={styles.sectionToolbar}>
        {panel === 'cerrado' && (
          <button className={styles.btnPrimary} onClick={abrirCrear}>
            <i className="ti ti-plus" aria-hidden="true" />
            Nueva jerarquía
          </button>
        )}
      </div>

      {panel !== 'cerrado' && (
        <JerarquiaForm
          mode={panel === 'crear' ? 'crear' : 'editar'}
          form={form}
          fieldErrors={fieldErrors}
          enviando={enviando}
          onChange={handleChange}
          onSubmit={handleSubmit}
          onCancel={cerrarPanel}
        />
      )}

      <div className={styles.card}>
        <JerarquiaTable
          jerarquias={jerarquias}
          loading={loading}
          error={error}
          onRetry={reload}
          onEditar={abrirEditar}
          onEliminar={handleEliminar}
          onCrearPrimero={abrirCrear}
        />
      </div>
    </>
  )
}
