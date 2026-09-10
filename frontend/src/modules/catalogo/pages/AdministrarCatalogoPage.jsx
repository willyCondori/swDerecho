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

const ESTADO_TABS = [
  { value: 'activas', label: 'Activas' },
  { value: 'eliminadas', label: 'Eliminadas' },
]

function RamasSection() {
  const {
    ramas, loading, error, reload,
    estadoFiltro, setEstadoFiltro,
    crearRama, actualizarRama, eliminarRama, activarRama,
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
    if (!window.confirm(`¿Eliminar la rama "${rama.nombre}"? Los artículos ya cargados con esta rama no se ven afectados, pero dejará de aparecer como opción al cargar nuevos documentos. Podrás recuperarla luego desde la pestaña "Eliminadas".`)) return
    try {
      await eliminarRama(rama.id)
    } catch (e) {
      window.alert(e?.response?.data?.detail || 'No se pudo eliminar la rama de derecho.')
    }
  }

  const handleRecuperar = async (rama) => {
    if (!window.confirm(`¿Recuperar la rama "${rama.nombre}"? Volverá a estar disponible como opción al cargar artículos.`)) return
    try {
      await activarRama(rama.id)
    } catch (e) {
      window.alert(e?.response?.data?.detail || 'No se pudo recuperar la rama de derecho.')
    }
  }

  return (
    <>
      <div className={styles.sectionToolbar}>
        <div className={styles.tabs}>
          {ESTADO_TABS.map((t) => (
            <button
              key={t.value}
              className={`${styles.tab} ${estadoFiltro === t.value ? styles.tabActive : ''}`}
              onClick={() => setEstadoFiltro(t.value)}
              type="button"
            >
              {t.label}
            </button>
          ))}
        </div>
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
          onRecuperar={handleRecuperar}
          onCrearPrimero={abrirCrear}
        />
      </div>
    </>
  )
}

function JerarquiasSection() {
  const {
    jerarquias, loading, error, reload,
    estadoFiltro, setEstadoFiltro,
    crearJerarquia, actualizarJerarquia, eliminarJerarquia, activarJerarquia,
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

  // Nivel que tenía la jerarquía en edición justo antes del último cambio
  // (guardado por el backend cuando se editó su nivel o cuando se corrió
  // en cascada por otra operación). Permite mostrar el botón "Volver al
  // nivel anterior" dentro del formulario de edición.
  const nivelAnteriorEdicion =
    panel && panel.editar && panel.editar.nivel_anterior != null
      ? panel.editar.nivel_anterior
      : null

  const volverNivelAnterior = () => {
    if (nivelAnteriorEdicion == null) return
    setForm((prev) => ({ ...prev, nivel: String(nivelAnteriorEdicion) }))
    if (fieldErrors.nivel) setFieldErrors((prev) => ({ ...prev, nivel: null }))
  }

  // Intenta guardar (crear o actualizar) una jerarquía. Si el backend
  // responde 409 (nivel ya ocupado por otra jerarquía activa), pregunta
  // al usuario si quiere continuar; si confirma, reenvía la misma
  // petición con confirmar_reemplazo=true para que el backend corra
  // hacia abajo los niveles siguientes. Si cancela, se aborta el guardado
  // sin mostrar un error de formulario.
  const guardarConConfirmacionDeNivel = async (guardar, payload) => {
    try {
      await guardar(payload)
    } catch (err) {
      const data = err?.response?.data
      if (err?.response?.status === 409 && data?.conflicto) {
        const siguienteNivel = data.nivel + 1
        const confirmar = window.confirm(
          `Esta jerarquía es mayor que "${data.existente.nombre}".\n\n` +
          `Si continúas, "${data.existente.nombre}" y las jerarquías con nivel ${data.nivel} en adelante ` +
          `pasarán al siguiente nivel (nivel ${data.nivel} → ${siguienteNivel}, ${siguienteNivel} → ${siguienteNivel + 1}, y así sucesivamente).\n\n` +
          `¿Deseas continuar?`
        )
        if (!confirmar) {
          const cancelado = new Error('Registro cancelado por el usuario.')
          cancelado.cancelado = true
          throw cancelado
        }
        await guardar({ ...payload, confirmar_reemplazo: true })
        return
      }
      throw err
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setEnviando(true)
    setFieldErrors({})
    try {
      const payload = { nombre: form.nombre, nivel: Number(form.nivel) }
      if (panel === 'crear') {
        await guardarConConfirmacionDeNivel(crearJerarquia, payload)
      } else if (panel && panel.editar) {
        await guardarConConfirmacionDeNivel(
          (p) => actualizarJerarquia(panel.editar.id, p),
          payload
        )
      }
      cerrarPanel()
    } catch (err) {
      if (!err?.cancelado) {
        setFieldErrors(extraerErroresCampo(err, 'No se pudo guardar la jerarquía.'))
      }
    } finally {
      setEnviando(false)
    }
  }

  const handleEliminar = async (jerarquia) => {
    if (!window.confirm(`¿Eliminar la jerarquía "${jerarquia.nombre}"? Las jerarquías con nivel mayor bajarán un puesto (por ejemplo, si eliminas el nivel ${jerarquia.nivel}, el nivel ${jerarquia.nivel + 1} pasará a ser ${jerarquia.nivel}). Las normas que ya la tienen asignada no se ven afectadas, pero dejará de aparecer como opción al cargar nuevos documentos. Podrás recuperarla luego desde la pestaña "Eliminadas".`)) return
    try {
      await eliminarJerarquia(jerarquia.id)
    } catch (e) {
      window.alert(e?.response?.data?.detail || 'No se pudo eliminar la jerarquía.')
    }
  }

  const handleRecuperar = async (jerarquia) => {
    if (!window.confirm(`¿Recuperar la jerarquía "${jerarquia.nombre}"? Volverá a estar disponible en su nivel original (nivel ${jerarquia.nivel}) como opción al cargar artículos.`)) return
    try {
      await guardarConConfirmacionDeNivel((p) => activarJerarquia(jerarquia.id, p), {})
    } catch (e) {
      if (!e?.cancelado) {
        window.alert(e?.response?.data?.detail || 'No se pudo recuperar la jerarquía.')
      }
    }
  }

  return (
    <>
      <div className={styles.sectionToolbar}>
        <div className={styles.tabs}>
          {ESTADO_TABS.map((t) => (
            <button
              key={t.value}
              className={`${styles.tab} ${estadoFiltro === t.value ? styles.tabActive : ''}`}
              onClick={() => setEstadoFiltro(t.value)}
              type="button"
            >
              {t.label}
            </button>
          ))}
        </div>
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
          nivelAnterior={nivelAnteriorEdicion}
          onVolverNivelAnterior={volverNivelAnterior}
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
          onRecuperar={handleRecuperar}
          onCrearPrimero={abrirCrear}
        />
      </div>
    </>
  )
}
