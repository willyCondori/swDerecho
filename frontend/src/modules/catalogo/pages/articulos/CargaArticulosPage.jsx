// modules/catalogo/pages/CargaArticulosPage.jsx
import { useEffect, useRef, useState } from 'react'
import cargaArticulosApi from '../../../../api/cargaArticulosApi'
import RevisionCargaPanel from '../../components/articulos/RevisionCargaPanel'
import { useCargaArticulos } from '../../hooks/useCargaArticulos'
import { useArchivoPdf } from '../../hooks/useArchivoPdf'
import { validarFormulario } from '../../utils/validation'
import FileDropzone from '../../components/articulos/FileDropzone'
import FormSelectField from '../../components/articulos/FormSelectField'
import FormTextField from '../../components/articulos/FormTextField'
import FuenteInfo from '../../components/articulos/FuenteInfo'
import ProgressPanel from '../../components/articulos/ProgressPanel'
import CargasEnCursoAviso from '../../components/articulos/CargasEnCursoAviso'
import ResultSummary from '../../components/articulos/ResultSummary'
import ErrorPanel from '../../components/articulos/ErrorPanel'
import WarningsList from '../../components/articulos/WarningsList'
import styles from './CargaArticulosPage.module.css'

// El formulario pide solo lo que hace falta para cargar CUALQUIER norma:
// rama de derecho, tipo de norma (jerarquía) y el nombre del documento en
// texto. Ya no hay un <select> fijo de "Civil / Penal / Laboral / CPE": el
// nombre que escribas (ej. "Código de Procedimiento Penal") crea o
// reutiliza la Norma automáticamente en el backend.
const FORM_INICIAL = {
  modo: 'nueva', // 'nueva' | 'existente'
  normaId: '',
  nombreDocumento: '', sigla: '', jerarquiaId: '', ramaId: '',
}

export default function CargaArticulosPage() {
  const {
    jerarquias, ramas, normas, loadingOpts,
    cargar, reset,
    enviando, procesando,
    progreso, paso, resumen, error, advertencias,
    cargaRetomada, otrasCargas,
  } = useCargaArticulos()

  const {
    fileInputRef, archivo, dragOver, error: archivoError,
    seleccionar, remover, handleDrop, handleDragOver, handleDragLeave, abrirSelector,
  } = useArchivoPdf()

  const [form, setForm] = useState(FORM_INICIAL)
  const [fieldErrors, setFieldErrors] = useState({})
  const [revision, setRevision] = useState(null)
  const [revisando, setRevisando] = useState(false)
  const [errorRevision, setErrorRevision] = useState('')
  const [modoActualizacion, setModoActualizacion] = useState('articulos')
  const [seleccion, setSeleccion] = useState([])
  const revisionActual = useRef(0)
  useEffect(() => { revisionActual.current++; setRevision(null); setErrorRevision(''); setRevisando(false) }, [archivo, form])

  const modoExistente = form.modo === 'existente'
  const normaSeleccionada = normas.find((n) => String(n.id) === String(form.normaId))
  const jerarquiaSeleccionada = modoExistente
    ? normaSeleccionada?.jerarquia
    : jerarquias.find((j) => String(j.id) === String(form.jerarquiaId))
  const mostrandoFormulario = !procesando && !resumen && !error

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
    if (fieldErrors[name]) setFieldErrors((prev) => ({ ...prev, [name]: null }))
  }

  const handleModoChange = (modo) => {
    if (modo === form.modo) return
    setForm((prev) => ({ ...prev, modo }))
    setFieldErrors({})
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errores = validarFormulario({ archivo, ...form })
    if (Object.keys(errores).length) {
      setFieldErrors(errores)
      return
    }
    const payload = {
      archivo,
      normaId: modoExistente ? form.normaId : null,
      nombreDocumento: modoExistente ? '' : form.nombreDocumento.trim(),
      sigla: modoExistente ? '' : form.sigla.trim(),
      jerarquiaId: modoExistente ? '' : form.jerarquiaId,
      ramaId: form.ramaId,
    }
    setRevisando(true)
    setErrorRevision('')
    const solicitud = ++revisionActual.current
    try {
      const { data } = await cargaArticulosApi.revisar(payload)
      if (solicitud !== revisionActual.current) return
      setRevision({ ...data, payload })
      setSeleccion(data.articulos.filter((a) => a.accion !== 'sin_cambios').map((a) => a.numero))
    } catch (err) {
      if (solicitud !== revisionActual.current) return
      const datos = err.response?.data
      const mensaje = datos?.detail || (datos && Object.values(datos).flat()[0])
      setErrorRevision(typeof mensaje === 'string' ? mensaje : 'No se pudo revisar el PDF. Vuelve a intentarlo.')
    } finally { if (solicitud === revisionActual.current) setRevisando(false) }
  }

  const handleReiniciar = () => {
    reset()
    remover()
    setForm(FORM_INICIAL)
    setFieldErrors({})
    setRevision(null)
  }

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <h1 className={styles.title}>Cargar artículos jurídicos</h1>
        <p className={styles.subtitle}>
          Sube el PDF de cualquier norma boliviana (Código Civil, Penal,
          Laboral, de Procedimiento Penal, la CPE, o cualquier otra).
          Indica la rama de derecho, el tipo de norma y el nombre del
          documento; el sistema extrae automáticamente cada artículo, lo
          guarda en el catálogo y genera su embedding semántico para el
          motor de búsqueda.
        </p>
      </header>

      {!resumen && <CargasEnCursoAviso cargas={otrasCargas} />}

      {mostrandoFormulario && !revision && (
        <form onSubmit={handleSubmit} noValidate>
          <div className={styles.card}>
            <h2 className={styles.cardTitle}>
              <i className={`ti ti-file-upload ${styles.cardTitleIcon}`} aria-hidden="true" />
              Documento PDF
            </h2>

            <FileDropzone
              archivo={archivo}
              dragOver={dragOver}
              error={fieldErrors.archivo || archivoError}
              fileInputRef={fileInputRef}
              onFileChange={seleccionar}
              onAbrirSelector={abrirSelector}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onRemover={remover}
            />

            <div className={styles.modoToggle} role="tablist" aria-label="Norma nueva o existente">
              <button
                type="button"
                role="tab"
                aria-selected={!modoExistente}
                className={`${styles.modoBtn} ${!modoExistente ? styles.modoBtnActive : ''}`}
                onClick={() => handleModoChange('nueva')}
              >
                <i className="ti ti-file-plus" aria-hidden="true" />
                Norma nueva
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={modoExistente}
                className={`${styles.modoBtn} ${modoExistente ? styles.modoBtnActive : ''}`}
                onClick={() => handleModoChange('existente')}
              >
                <i className="ti ti-replace" aria-hidden="true" />
                Norma existente
              </button>
            </div>

            <div className={styles.formGrid}>
              {modoExistente ? (
                <FormSelectField
                  id="normaId"
                  label="Norma"
                  placeholder={loadingOpts ? 'Cargando normas...' : 'Selecciona la norma...'}
                  value={form.normaId}
                  onChange={handleInputChange}
                  options={normas.map((n) => ({
                    value: n.id,
                    label: n.sigla ? `${n.nombre} (${n.sigla})` : n.nombre,
                  }))}
                  disabled={loadingOpts}
                  error={fieldErrors.normaId}
                  fullWidth
                />
              ) : (
                <>
                  <FormTextField
                    id="nombreDocumento"
                    label="Nombre del documento"
                    placeholder="Ej. Código de Procedimiento Penal"
                    value={form.nombreDocumento}
                    onChange={handleInputChange}
                    disabled={loadingOpts}
                    error={fieldErrors.nombreDocumento}
                    helpText="Si ya existe una norma con este nombre, se reutiliza; si no, se crea."
                    fullWidth
                  />

                  <FormTextField
                    id="sigla"
                    label="Sigla (opcional)"
                    placeholder="Ej. CPP"
                    value={form.sigla}
                    onChange={handleInputChange}
                    disabled={loadingOpts}
                    error={fieldErrors.sigla}
                    helpText="Si ya existe una norma con esta sigla, se reutiliza en lugar de crear una nueva."
                  />

                  <FormSelectField
                    id="jerarquiaId"
                    label="Tipo de norma (jerarquía)"
                    placeholder="Selecciona una jerarquía..."
                    value={form.jerarquiaId}
                    onChange={handleInputChange}
                    options={jerarquias.map((j) => ({
                      value: j.id,
                      label: `${j.nombre} (nivel ${j.nivel})`,
                    }))}
                    disabled={loadingOpts}
                    error={fieldErrors.jerarquiaId}
                  />
                </>
              )}

              <FormSelectField
                id="ramaId"
                label="Rama de derecho"
                placeholder="Selecciona una rama..."
                value={form.ramaId}
                onChange={handleInputChange}
                options={ramas.map((r) => ({ value: r.id, label: r.nombre }))}
                disabled={loadingOpts}
                error={fieldErrors.ramaId}
                fullWidth={modoExistente}
              />
            </div>

            <FuenteInfo jerarquia={jerarquiaSeleccionada} />

            <div className={styles.submitRow}>
              <button type="button" className={styles.btnSecondary} onClick={handleReiniciar}>
                Limpiar
              </button>
              <button type="submit" className={styles.btnPrimary} disabled={enviando || revisando || loadingOpts}>
                {revisando ? (
                  <>
                    <span className={styles.spinner} aria-hidden="true" />
                    Revisando PDF…
                  </>
                ) : (
                  <>
                    <i className="ti ti-upload" aria-hidden="true" />
                    Revisar PDF antes de cargar
                  </>
                )}
              </button>
            </div>
          </div>
          {errorRevision && <p role="alert" className={styles.reviewWarning}>{errorRevision}</p>}
        </form>
      )}

      {mostrandoFormulario && revision && <RevisionCargaPanel revision={revision} modo={modoActualizacion}
        onModo={setModoActualizacion} seleccion={seleccion} onSeleccion={setSeleccion} enviando={enviando}
        onCancelar={() => setRevision(null)} onConfirmar={() => cargar({ ...revision.payload,
          modoActualizacion, revisionToken: revision.revision_token, articulosSeleccionados: seleccion })} />}

      {procesando && (
        <ProgressPanel
          paso={paso}
          progreso={progreso}
          documento={cargaRetomada?.nombre_documento || (modoExistente ? normaSeleccionada?.nombre : form.nombreDocumento.trim())}
          retomada={Boolean(cargaRetomada)}
        />
      )}

      {resumen && <ResultSummary resumen={resumen} onReiniciar={handleReiniciar} />}

      {error && !procesando && <ErrorPanel mensaje={error} onReintentar={handleReiniciar} />}

      {!resumen && !error && <WarningsList advertencias={advertencias} />}
    </div>
  )
}
