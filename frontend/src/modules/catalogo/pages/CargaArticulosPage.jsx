// modules/catalogo/pages/CargaArticulosPage.jsx
import { useRef, useState } from 'react'
import { useCargaArticulos } from '../hooks/useCargaArticulos'
import styles from './CargaArticulosPage.module.css'

const MAX_SIZE_MB = 50

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function CargaArticulosPage() {
  const {
    fuentes, normas, ramas, loadingOpts,
    cargar, reset,
    enviando, procesando,
    estado, progreso, paso, resumen, error, advertencias,
  } = useCargaArticulos()

  const fileInputRef = useRef(null)
  const [archivo, setArchivo]   = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [form, setForm] = useState({
    fuente: '', normaId: '', ramaId: '', sobrescribir: false,
  })
  const [fieldErrors, setFieldErrors] = useState({})

  const fuenteSeleccionada = fuentes.find((f) => f.value === form.fuente)

  // ── Manejo de archivo ────────────────────────────────────
  const validarArchivo = (file) => {
    if (!file) return null
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      return 'Solo se aceptan archivos PDF (.pdf).'
    }
    const sizeMb = file.size / (1024 * 1024)
    if (sizeMb > MAX_SIZE_MB) {
      return `El archivo supera el máximo de ${MAX_SIZE_MB} MB (${sizeMb.toFixed(1)} MB).`
    }
    return null
  }

  const handleFile = (file) => {
    const err = validarArchivo(file)
    if (err) {
      setFieldErrors((p) => ({ ...p, archivo: err }))
      return
    }
    setFieldErrors((p) => ({ ...p, archivo: null }))
    setArchivo(file)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) handleFile(file)
  }

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((p) => ({ ...p, [name]: type === 'checkbox' ? checked : value }))
    if (fieldErrors[name]) setFieldErrors((p) => ({ ...p, [name]: null }))
  }

  const removeArchivo = () => {
    setArchivo(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  // ── Validación y envío ──────────────────────────────────
  const validate = () => {
    const errs = {}
    if (!archivo)        errs.archivo  = 'Debes seleccionar un archivo PDF.'
    if (!form.fuente)    errs.fuente   = 'Selecciona el tipo de norma.'
    if (!form.normaId)   errs.normaId  = 'Selecciona la norma destino.'
    if (!form.ramaId)    errs.ramaId   = 'Selecciona la rama de derecho.'
    return errs
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) {
      setFieldErrors(errs)
      return
    }
    await cargar({
      archivo,
      fuente:       form.fuente,
      normaId:      form.normaId,
      ramaId:       form.ramaId,
      sobrescribir: form.sobrescribir,
    })
  }

  const handleReiniciar = () => {
    reset()
    removeArchivo()
    setForm({ fuente: '', normaId: '', ramaId: '', sobrescribir: false })
    setFieldErrors({})
  }

  const mostrandoFormulario = !procesando && !resumen && !error

  return (
    <div className={styles.root}>
      {/* ── Encabezado ───────────────────────────────── */}
      <header className={styles.header}>
        <h1 className={styles.title}>Cargar artículos jurídicos</h1>
        <p className={styles.subtitle}>
          Sube el PDF de un código o norma boliviana (Código Civil, Penal,
          Laboral o la CPE). El sistema extrae automáticamente cada
          artículo, lo guarda en el catálogo y genera su embedding
          semántico para el motor de búsqueda.
        </p>
      </header>

      {/* ── Formulario ──────────────────────────────── */}
      {mostrandoFormulario && (
        <form onSubmit={handleSubmit} noValidate>
          <div className={styles.card}>
            <h2 className={styles.cardTitle}>
              <i className={`ti ti-file-upload ${styles.cardTitleIcon}`} aria-hidden="true" />
              Documento PDF
            </h2>

            {/* Dropzone */}
            <div
              className={`${styles.dropzone} ${dragOver ? styles.dragOver : ''} ${archivo ? styles.hasFile : ''}`}
              onClick={() => !archivo && fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              role="button"
              tabIndex={0}
              aria-label="Seleccionar archivo PDF"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf,.pdf"
                className={styles.fileInput}
                onChange={(e) => handleFile(e.target.files?.[0])}
              />

              {!archivo ? (
                <>
                  <div className={styles.dropzoneIcon}>
                    <i className="ti ti-cloud-upload" aria-hidden="true" />
                  </div>
                  <p className={styles.dropzoneText}>
                    <strong>Haz clic para subir</strong> o arrastra el archivo aquí
                  </p>
                  <p className={styles.dropzoneHint}>
                    Solo PDF · Máximo {MAX_SIZE_MB} MB
                  </p>
                </>
              ) : (
                <div className={styles.filePreview}>
                  <div className={styles.fileIconBox}>
                    <i className="ti ti-file-type-pdf" aria-hidden="true" />
                  </div>
                  <div className={styles.fileInfo}>
                    <p className={styles.fileName}>{archivo.name}</p>
                    <p className={styles.fileSize}>{formatBytes(archivo.size)}</p>
                  </div>
                  <button
                    type="button"
                    className={styles.fileRemove}
                    onClick={(e) => { e.stopPropagation(); removeArchivo() }}
                    aria-label="Quitar archivo"
                  >
                    <i className="ti ti-x" aria-hidden="true" />
                  </button>
                </div>
              )}
            </div>
            {fieldErrors.archivo && (
              <span className={styles.fieldError}>
                <i className="ti ti-alert-circle" aria-hidden="true" />
                {fieldErrors.archivo}
              </span>
            )}

            {/* Campos del formulario */}
            <div className={styles.formGrid}>
              {/* Fuente */}
              <div className={styles.field}>
                <label htmlFor="fuente" className={styles.label}>
                  Tipo de norma
                </label>
                <select
                  id="fuente"
                  name="fuente"
                  className={styles.select}
                  value={form.fuente}
                  onChange={handleInputChange}
                  disabled={loadingOpts}
                >
                  <option value="">Selecciona una fuente...</option>
                  {fuentes.map((f) => (
                    <option key={f.value} value={f.value}>{f.label}</option>
                  ))}
                </select>
                {fieldErrors.fuente && (
                  <span className={styles.fieldError}>
                    <i className="ti ti-alert-circle" aria-hidden="true" />
                    {fieldErrors.fuente}
                  </span>
                )}
              </div>

              {/* Norma */}
              <div className={styles.field}>
                <label htmlFor="normaId" className={styles.label}>
                  Norma destino
                </label>
                <select
                  id="normaId"
                  name="normaId"
                  className={styles.select}
                  value={form.normaId}
                  onChange={handleInputChange}
                  disabled={loadingOpts}
                >
                  <option value="">Selecciona una norma...</option>
                  {normas.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.sigla ? `${n.sigla} — ${n.nombre}` : n.nombre}
                    </option>
                  ))}
                </select>
                {fieldErrors.normaId && (
                  <span className={styles.fieldError}>
                    <i className="ti ti-alert-circle" aria-hidden="true" />
                    {fieldErrors.normaId}
                  </span>
                )}
              </div>

              {/* Rama */}
              <div className={`${styles.field} ${styles.fullWidth}`}>
                <label htmlFor="ramaId" className={styles.label}>
                  Rama de derecho
                </label>
                <select
                  id="ramaId"
                  name="ramaId"
                  className={styles.select}
                  value={form.ramaId}
                  onChange={handleInputChange}
                  disabled={loadingOpts}
                >
                  <option value="">Selecciona una rama...</option>
                  {ramas.map((r) => (
                    <option key={r.id} value={r.id}>{r.nombre}</option>
                  ))}
                </select>
                {fieldErrors.ramaId && (
                  <span className={styles.fieldError}>
                    <i className="ti ti-alert-circle" aria-hidden="true" />
                    {fieldErrors.ramaId}
                  </span>
                )}
              </div>
            </div>

            {/* Info de la fuente seleccionada */}
            {fuenteSeleccionada && (
              <div className={styles.fuenteInfo}>
                <i className={`ti ti-info-circle ${styles.fuenteInfoIcon}`} aria-hidden="true" />
                <p className={styles.fuenteInfoText}>
                  {fuenteSeleccionada.descripcion}
                  {' · '}
                  <strong>Jerarquía normativa: {fuenteSeleccionada.jerarquia}</strong>
                  {fuenteSeleccionada.esperados && (
                    <> · Aprox. {fuenteSeleccionada.esperados} artículos esperados</>
                  )}
                </p>
              </div>
            )}

            {/* Checkbox sobrescribir */}
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

            {/* Acciones */}
            <div className={styles.submitRow}>
              <button
                type="button"
                className={styles.btnSecondary}
                onClick={handleReiniciar}
              >
                Limpiar
              </button>
              <button
                type="submit"
                className={styles.btnPrimary}
                disabled={enviando || loadingOpts}
              >
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

      {/* ── Panel de progreso ───────────────────────── */}
      {procesando && (
        <div className={styles.progressCard}>
          <div className={styles.progressHeader}>
            <div className={`${styles.progressIcon} ${styles.spinning}`}>
              <i className="ti ti-loader-2" aria-hidden="true" />
            </div>
            <div>
              <p className={styles.progressTitle}>Procesando documento...</p>
              <p className={styles.progressStep}>{paso || 'Iniciando...'}</p>
            </div>
          </div>
          <div className={styles.progressBarBg}>
            <div className={styles.progressBar} style={{ width: `${progreso}%` }} />
          </div>
          <p className={styles.progressPercent}>{progreso}%</p>
        </div>
      )}

      {/* ── Resultado exitoso ───────────────────────── */}
      {resumen && (
        <div className={styles.resultCard}>
          <div className={styles.resultHeader}>
            <div className={styles.resultIcon}>
              <i className="ti ti-circle-check" aria-hidden="true" />
            </div>
            <div>
              <p className={styles.resultTitle}>Procesamiento completado</p>
              <p className={styles.resultSubtitle}>
                {resumen.norma} · {resumen.rama} · Fuente: {resumen.fuente}
              </p>
            </div>
          </div>

          <div className={styles.statsGrid}>
            <div className={styles.statBox}>
              <p className={styles.statValue}>{resumen.total_encontrados}</p>
              <p className={styles.statLabel}>Encontrados</p>
            </div>
            <div className={styles.statBox}>
              <p className={`${styles.statValue} ${styles.green}`}>{resumen.guardados}</p>
              <p className={styles.statLabel}>Guardados</p>
            </div>
            <div className={styles.statBox}>
              <p className={`${styles.statValue} ${styles.amber}`}>{resumen.duplicados}</p>
              <p className={styles.statLabel}>Duplicados</p>
            </div>
            <div className={styles.statBox}>
              <p className={`${styles.statValue} ${resumen.errores > 0 ? styles.red : ''}`}>
                {resumen.errores}
              </p>
              <p className={styles.statLabel}>Errores</p>
            </div>
          </div>

          {resumen.errores_detalle?.length > 0 && (
            <div className={styles.errorsList}>
              <p className={styles.errorsTitle}>Detalle de errores</p>
              {resumen.errores_detalle.map((err, i) => (
                <p key={i} className={styles.errorItem}>{err}</p>
              ))}
            </div>
          )}

          <div className={styles.resultActions}>
            <button className={styles.btnSecondary} onClick={handleReiniciar}>
              <i className="ti ti-plus" aria-hidden="true" />
              Cargar otro documento
            </button>
          </div>
        </div>
      )}

      {/* ── Error global ────────────────────────────── */}
      {error && !procesando && (
        <div className={styles.errorCard}>
          <div className={styles.errorCardIcon}>
            <i className="ti ti-alert-triangle" aria-hidden="true" />
          </div>
          <div style={{ flex: 1 }}>
            <p className={styles.errorCardTitle}>No se pudo completar la carga</p>
            <p className={styles.errorCardText}>{error}</p>
            <div className={styles.resultActions} style={{ marginTop: 16 }}>
              <button className={styles.btnSecondary} onClick={handleReiniciar}>
                Reintentar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Advertencias (antes de procesar) ─────────── */}
      {advertencias.length > 0 && !resumen && !error && (
        <>
          {advertencias.map((aviso, i) => (
            <div key={i} className={styles.warningBox}>
              <i className={`ti ti-alert-triangle ${styles.warningIcon}`} aria-hidden="true" />
              <p className={styles.warningText}>{aviso}</p>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
