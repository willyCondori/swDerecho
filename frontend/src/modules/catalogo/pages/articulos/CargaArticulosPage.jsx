// modules/catalogo/pages/CargaArticulosPage.jsx
import { useCallback, useEffect, useState } from 'react'
import { useRevisionPdf } from '../../hooks/useRevisionPdf'
import GacetaPanel from '../../components/articulos/GacetaPanel'
import RevisionCargaPanel from '../../components/articulos/RevisionCargaPanel'
import { useCargaArticulos } from '../../hooks/useCargaArticulos'
import { useBorradorCarga } from '../../hooks/useBorradorCarga'
import { useArchivoPdf } from '../../hooks/useArchivoPdf'
import { ramaDeNorma } from '../../utils/ramaNorma'
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
  motorLectura: 'clasico', tipoNorma: '', numeroNorma: '', fechaNorma: '', fechaPublicacion: '', urlFuente: '', documentoOficialId: null,
}

export default function CargaArticulosPage() {
  const {
    jerarquias, ramas, normas, loadingOpts,
    cargar, reset,
    enviando, procesando,
    progreso, paso, resumen, error, advertencias,
    cargaRetomada, otrasCargas, verificandoCargas,
  } = useCargaArticulos()

  const { borrador, actualizar: actualizarBorrador, limpiar: limpiarBorrador } = useBorradorCarga(FORM_INICIAL)
  const setArchivoBorrador = useCallback((archivo) => actualizarBorrador({ archivo }), [actualizarBorrador])
  const {
    fileInputRef, archivo, dragOver, error: archivoError,
    seleccionar, remover, handleDrop, handleDragOver, handleDragLeave, abrirSelector,
  } = useArchivoPdf({ archivo: borrador.archivo, onArchivo: setArchivoBorrador })

  const form = borrador.form
  const setForm = (valor) => actualizarBorrador((b) => ({ form: typeof valor === 'function' ? valor(b.form) : valor }))
  const [fieldErrors, setFieldErrors] = useState({})
  const { revision, revisando, pasoRevision, errorRevision, documento: documentoRevision, revisarPdf, limpiarRevision } = useRevisionPdf()
  const [revisionRetomada, setRevisionRetomada] = useState(revisando)
  const modoActualizacion = borrador.modo
  const setModoActualizacion = (modo) => actualizarBorrador({ modo })
  const seleccion = borrador.seleccion
  const setSeleccion = (seleccion) => actualizarBorrador({ seleccion })
  useEffect(() => {
    if (revision && borrador.revisionSeleccion !== revision) actualizarBorrador({ revisionSeleccion: revision, seleccion: revision.articulos.filter((a) => a.accion !== 'sin_cambios').map((a) => a.numero) })
  }, [revision, borrador.revisionSeleccion, actualizarBorrador])

  const modoExistente = form.modo === 'existente'
  const normaSeleccionada = normas.find((n) => String(n.id) === String(form.normaId))
  const jerarquiaSeleccionada = modoExistente
    ? normaSeleccionada?.jerarquia
    : jerarquias.find((j) => String(j.id) === String(form.jerarquiaId))
  const mostrandoFormulario = !verificandoCargas && !revisando && !procesando && !resumen && !error

  useEffect(() => {
    if (form.modo !== 'existente' || form.ramaId || loadingOpts) return
    const ramaId = ramaDeNorma(normas.find((n) => String(n.id) === String(form.normaId)), ramas)
    if (ramaId) actualizarBorrador((b) => ({ form: { ...b.form, ramaId } }))
  }, [form.modo, form.normaId, form.ramaId, loadingOpts, normas, ramas, actualizarBorrador])

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target
    const elegida = name === 'normaId' ? normas.find((n) => String(n.id) === String(value)) : null
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value,
      ...(name === 'normaId' ? { ramaId: ramaDeNorma(elegida, ramas) } : {}) }))
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
      motorLectura: form.motorLectura,
      documentoOficialId: form.documentoOficialId,
      metadatos: Object.fromEntries(Object.entries({ tipo_norma: form.tipoNorma, numero_norma: form.numeroNorma,
        fecha_norma: form.fechaNorma, fecha_publicacion: form.fechaPublicacion, url_fuente: form.urlFuente }).filter(([, v]) => v)),
    }
    setRevisionRetomada(false)
    await revisarPdf(payload)
  }

  const elegirOficial = (documento, pdf) => {
    seleccionar(pdf)
    setForm({ ...FORM_INICIAL, motorLectura: form.motorLectura, nombreDocumento: documento.titulo, tipoNorma: documento.tipo,
      numeroNorma: documento.numero, fechaPublicacion: documento.fecha_publicacion || '',
      urlFuente: documento.url_fuente, documentoOficialId: documento.id,
      ramaId: ramas.find((r) => /penal/i.test(r.nombre))?.id || '',
      jerarquiaId: jerarquias.find((j) => j.nombre.toLowerCase() === documento.tipo.toLowerCase())?.id || '',
    })
    setFieldErrors({}); limpiarRevision()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleReiniciar = () => {
    reset()
    remover()
    setForm(FORM_INICIAL)
    setFieldErrors({})
    limpiarRevision()
    limpiarBorrador()
  }

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <h1 className={styles.title}>Cargar artículos jurídicos</h1>
        <p className={styles.subtitle}>
          Sube el PDF de cualquier norma boliviana (Código Civil, Penal,
          Laboral, de Procedimiento Penal, la CPE, o cualquier otra).
          Revisa sus artículos y disposiciones antes de incorporarlos al catálogo.
          Los cambios normativos detectados se mostrarán con su alcance,
          fecha y documento de respaldo.
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
              {modoExistente && normaSeleccionada?.ramas?.length > 1 && <p>Esta norma está asociada a varias ramas. Selecciona la correspondiente a este documento.</p>}
            </div>

            <fieldset className={styles.modeOptions}>
              <legend>Lectura y datos de la publicación</legend>
              <FormSelectField id="motorLectura" label="Lectura del documento" value={form.motorLectura} onChange={handleInputChange}
                options={[{ value: 'clasico', label: 'Algoritmos locales: lectura y efectos expresos, sin Qwen' }, { value: 'qwen', label: 'Qwen opcional: lectura asistida por IA' }]} />
              <p>Los algoritmos conservan el texto original y detectan efectos expresos. Qwen es opcional y consume más recursos. Verifica los datos de la norma antes de confirmar.</p>
              <div className={styles.formGrid}>
                <FormTextField id="tipoNorma" label="Tipo legal (opcional)" value={form.tipoNorma} onChange={handleInputChange} placeholder="Ley, Decreto Supremo, Resolución…" />
                <FormTextField id="numeroNorma" label="Número legal (opcional)" value={form.numeroNorma} onChange={handleInputChange} />
                <FormTextField id="fechaNorma" label="Fecha de promulgación (YYYY-MM-DD)" value={form.fechaNorma} onChange={handleInputChange} />
                <FormTextField id="fechaPublicacion" label="Fecha de publicación (YYYY-MM-DD)" value={form.fechaPublicacion} onChange={handleInputChange} />
                <FormTextField id="urlFuente" label="Enlace de la publicación oficial (opcional)" value={form.urlFuente} onChange={handleInputChange} fullWidth />
              </div>
            </fieldset>
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
        </form>
      )}

      {mostrandoFormulario && revision && <RevisionCargaPanel revision={revision} modo={modoActualizacion}
        onModo={setModoActualizacion} seleccion={seleccion} onSeleccion={setSeleccion} enviando={enviando}
        onCancelar={limpiarRevision} onSeccion={async (id) => {
          setModoActualizacion('articulos')
          const seccion = revision.secciones_documento.find((s) => s.id === id)
          const clave = (s) => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim()
          const legal = /^(ley|decreto ley|decreto supremo|resolucion ministerial)[^\d]*(\d+)/.exec(clave(seccion.titulo))
          const destino = normas.find((n) => clave(n.nombre) === clave(seccion.titulo) ||
            (/^codigo /.test(clave(seccion.titulo)) && clave(n.nombre).startsWith(clave(seccion.titulo))) ||
            (legal && clave(n.tipo_norma) === legal[1] && Number(n.numero_norma) === Number(legal[2])))
          await revisarPdf({ ...revision.payload, seccionDocumento: id, variantesUnidades: {},
            normaId: destino?.id || null, nombreDocumento: seccion.titulo, sigla: '', documentoOficialId: null,
            jerarquiaId: destino?.jerarquia?.id || revision.payload.jerarquiaId || jerarquias.find((j) => /ley/i.test(j.nombre))?.id,
            metadatos: revision.payload.metadatos?.url_fuente ? { url_fuente: revision.payload.metadatos.url_fuente } : {} })
        }} onIdentidad={async ({ nombre, numero, fecha }) => {
          const destino = normas.find((n) => n.tipo_norma?.toLowerCase() === 'ley' && Number(n.numero_norma) === Number(numero))
          await revisarPdf({ ...revision.payload, normaId: destino?.id || null, nombreDocumento: nombre.trim(), sigla: '', documentoOficialId: null,
            jerarquiaId: destino?.jerarquia?.id || revision.payload.jerarquiaId || jerarquias.find((j) => /ley/i.test(j.nombre))?.id,
            metadatos: { ...revision.payload.metadatos, tipo_norma: 'Ley', numero_norma: numero.trim(), fecha_norma: fecha } })
        }} onAlternativa={async (clave, id) => {
          await revisarPdf({ ...revision.payload, variantesUnidades: { ...revision.payload.variantesUnidades, [clave]: id } })
        }} onConfirmar={async () => {
          const resultado = await cargar({ ...revision.payload, modoActualizacion,
            revisionToken: revision.revision_token, articulosSeleccionados: seleccion })
          if (resultado.success) { limpiarRevision(); limpiarBorrador() }
        }} />}

      {verificandoCargas && <p role="status">Verificando si hay un PDF en procesamiento…</p>}
      {revisando && <ProgressPanel paso={pasoRevision} progreso={null} documento={documentoRevision} retomada={revisionRetomada} />}
      {errorRevision && !revisando && !revision && <p role="alert">{errorRevision}</p>}

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

      {mostrandoFormulario && !revision && <GacetaPanel onElegir={elegirOficial} />}
      {!resumen && !error && <WarningsList advertencias={advertencias} />}
    </div>
  )
}
