// modules/catalogo/pages/CargaArticulosPage.jsx
import { useState } from 'react'
import { useCargaArticulos } from '../../hooks/useCargaArticulos'
import { useArchivoPdf } from '../../hooks/useArchivoPdf'
import { validarFormulario } from '../../utils/validation'
import FileDropzone from '../../components/articulos/FileDropzone'
import FormSelectField from '../../components/articulos/FormSelectField'
import FormTextField from '../../components/articulos/FormTextField'
import FuenteInfo from '../../components/articulos/FuenteInfo'
import ProgressPanel from '../../components/articulos/ProgressPanel'
import ResultSummary from '../../components/articulos/ResultSummary'
import ErrorPanel from '../../components/articulos/ErrorPanel'
import WarningsList from '../../components/articulos/WarningsList'
import styles from './CargaArticulosPage.module.css'

// El formulario pide solo lo que hace falta para cargar CUALQUIER norma:
// rama de derecho, tipo de norma (jerarquía) y el nombre del documento en
// texto. Ya no hay un <select> fijo de "Civil / Penal / Laboral / CPE": el
// nombre que escribas (ej. "Código de Procedimiento Penal") crea o
// reutiliza la Norma automáticamente en el backend.
const FORM_INICIAL = { nombreDocumento: '', sigla: '', jerarquiaId: '', ramaId: '', sobrescribir: false }

export default function CargaArticulosPage() {
  const {
    jerarquias, ramas, loadingOpts,
    cargar, reset,
    enviando, procesando,
    progreso, paso, resumen, error, advertencias,
  } = useCargaArticulos()

  const {
    fileInputRef, archivo, dragOver, error: archivoError,
    seleccionar, remover, handleDrop, handleDragOver, handleDragLeave, abrirSelector,
  } = useArchivoPdf()

  const [form, setForm] = useState(FORM_INICIAL)
  const [fieldErrors, setFieldErrors] = useState({})

  const jerarquiaSeleccionada = jerarquias.find((j) => String(j.id) === String(form.jerarquiaId))
  const mostrandoFormulario = !procesando && !resumen && !error

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
    if (fieldErrors[name]) setFieldErrors((prev) => ({ ...prev, [name]: null }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errores = validarFormulario({ archivo, ...form })
    if (Object.keys(errores).length) {
      setFieldErrors(errores)
      return
    }
    await cargar({
      archivo,
      nombreDocumento: form.nombreDocumento.trim(),
      sigla: form.sigla.trim(),
      jerarquiaId: form.jerarquiaId,
      ramaId: form.ramaId,
      sobrescribir: form.sobrescribir,
    })
  }

  const handleReiniciar = () => {
    reset()
    remover()
    setForm(FORM_INICIAL)
    setFieldErrors({})
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

      {mostrandoFormulario && (
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

            <div className={styles.formGrid}>
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

              <FormSelectField
                id="ramaId"
                label="Rama de derecho"
                placeholder="Selecciona una rama..."
                value={form.ramaId}
                onChange={handleInputChange}
                options={ramas.map((r) => ({ value: r.id, label: r.nombre }))}
                disabled={loadingOpts}
                error={fieldErrors.ramaId}
              />
            </div>

            <FuenteInfo jerarquia={jerarquiaSeleccionada} />
{/* 
            <div className={styles.checkboxRow}>
              <input
                id="sobrescribir"
                name="sobrescribir"
                type="checkbox"
                className={styles.checkbox}
                checked={form.sobrescribir}
                onChange={handleInputChange}
              />
              <label htmlFor="sobrescribir" className={styles.checkboxLabel}>
                <strong>Sobrescribir artículos existentes.</strong> Si esta norma y
                rama ya tienen artículos cargados, serán eliminados antes de
                insertar los nuevos. Si no marcas esta opción, los artículos
                duplicados simplemente se omitirán.
              </label>
            </div>
*/}

            <div className={styles.submitRow}>
              <button type="button" className={styles.btnSecondary} onClick={handleReiniciar}>
                Limpiar
              </button>
              <button type="submit" className={styles.btnPrimary} disabled={enviando || loadingOpts}>
                {enviando ? (
                  <>
                    <span className={styles.spinner} aria-hidden="true" />
                    Enviando...
                  </>
                ) : (
                  <>
                    <i className="ti ti-upload" aria-hidden="true" />
                    Procesar PDF
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      )}

      {procesando && <ProgressPanel paso={paso} progreso={progreso} />}

      {resumen && <ResultSummary resumen={resumen} onReiniciar={handleReiniciar} />}

      {error && !procesando && <ErrorPanel mensaje={error} onReintentar={handleReiniciar} />}

      {!resumen && !error && <WarningsList advertencias={advertencias} />}
    </div>
  )
}
