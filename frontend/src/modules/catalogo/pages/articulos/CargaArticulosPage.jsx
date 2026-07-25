// modules/catalogo/pages/CargaArticulosPage.jsx
import { useState } from 'react'
import { useCargaArticulos } from '../../hooks/useCargaArticulos'
import { useArchivoPdf } from '../../hooks/useArchivoPdf'
import { validarFormulario } from '../../utils/validation'
import FileDropzone from '../../components/articulos/FileDropzone'
import FormSelectField from '../../components/articulos/FormSelectField'
import FuenteInfo from '../../components/articulos/FuenteInfo'
import ProgressPanel from '../../components/articulos/ProgressPanel'
import ResultSummary from '../../components/articulos/ResultSummary'
import ErrorPanel from '../../components/articulos/ErrorPanel'
import WarningsList from '../../components/articulos/WarningsList'
import styles from './CargaArticulosPage.module.css'

const FORM_INICIAL = { fuente: '', normaId: '', ramaId: '', sobrescribir: false }

export default function CargaArticulosPage() {
  const {
    fuentes, normas, ramas, loadingOpts,
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

  const fuenteSeleccionada = fuentes.find((f) => f.value === form.fuente)
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
      fuente: form.fuente,
      normaId: form.normaId,
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
          Sube el PDF de un código o norma boliviana (Código Civil, Penal,
          Laboral o la CPE). El sistema extrae automáticamente cada
          artículo, lo guarda en el catálogo y genera su embedding
          semántico para el motor de búsqueda.
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
              <FormSelectField
                id="fuente"
                label="Tipo de norma"
                placeholder="Selecciona una fuente..."
                value={form.fuente}
                onChange={handleInputChange}
                options={fuentes}
                disabled={loadingOpts}
                error={fieldErrors.fuente}
              />

              <FormSelectField
                id="normaId"
                label="Norma destino"
                placeholder="Selecciona una norma..."
                value={form.normaId}
                onChange={handleInputChange}
                options={normas.map((n) => ({
                  value: n.id,
                  label: n.sigla ? `${n.sigla} — ${n.nombre}` : n.nombre,
                }))}
                disabled={loadingOpts}
                error={fieldErrors.normaId}
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
                fullWidth
              />
            </div>

            <FuenteInfo fuente={fuenteSeleccionada} />

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