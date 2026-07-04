// modules/casos/pages/NuevoCasoPage.jsx
import { useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import useCrearCaso from '../hooks/useCrearCaso'
import styles from './NuevoCasoPage.module.css'

export default function NuevoCasoPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)
  const {
    form, clienteForm, modo, archivo, fieldErrors, enviando, error,
    onChange, onArchivoChange, cambiarModo, onSubmit,
  } = useCrearCaso()

  return (
    <div className={styles.root}>
      <div className={styles.headerRow}>
        <button type="button" className={styles.backBtn} onClick={() => navigate('/casos')} aria-label="Volver">
          <i className="ti ti-arrow-left" aria-hidden="true" />
        </button>
        <div>
          <h1 className={styles.title}>Nuevo caso</h1>
          <p className={styles.subtitle}>Registra al cliente y describe el caso con texto o un PDF.</p>
        </div>
      </div>

      {error && <div className={styles.errorBanner}>{error}</div>}

      <form onSubmit={onSubmit} noValidate>
        <div className={styles.card}>

          <h2 className={styles.cardTitle}>
            <i className="ti ti-user-plus" aria-hidden="true" /> Datos del cliente
          </h2>

          <div className={styles.formGrid}>
            <div className={styles.field}>
              <label className={styles.label}>Nombres</label>
              <input className={styles.input} name="nombres" value={clienteForm.nombres} onChange={onChange} placeholder="Nombres" />
              {fieldErrors.nombres && <span className={styles.fieldError}>{fieldErrors.nombres}</span>}
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Apellidos</label>
              <input className={styles.input} name="apellidos" value={clienteForm.apellidos} onChange={onChange} placeholder="Apellidos" />
              {fieldErrors.apellidos && <span className={styles.fieldError}>{fieldErrors.apellidos}</span>}
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Email</label>
              <input className={styles.input} type="email" name="email" value={clienteForm.email} onChange={onChange} placeholder="ejemplo@correo.com" />
              {fieldErrors.email && <span className={styles.fieldError}>{fieldErrors.email}</span>}
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Teléfono</label>
              <input
                className={styles.input}
                type="text"
                name="telefono"
                value={clienteForm.telefono}
                onChange={(e) => {
                  const soloNumeros = e.target.value.replace(/[^0-9]/g, '')
                  onChange({ target: { name: 'telefono', value: soloNumeros.slice(0, 8) } })
                }}
                placeholder="7########"
              />
              {fieldErrors.telefono && <span className={styles.fieldError}>{fieldErrors.telefono}</span>}
            </div>
          </div>

          <h2 className={styles.cardTitle} style={{ marginTop: 'var(--sp-4)' }}>
            <i className="ti ti-briefcase" aria-hidden="true" /> Datos del caso
          </h2>

          <div className={styles.tabs}>
            <button
              type="button"
              className={`${styles.tab} ${modo === 'texto' ? styles.tabActive : ''}`}
              onClick={() => cambiarModo('texto')}
            >
              <i className="ti ti-align-left" aria-hidden="true" /> Texto
            </button>
            <button
              type="button"
              className={`${styles.tab} ${modo === 'pdf' ? styles.tabActive : ''}`}
              onClick={() => cambiarModo('pdf')}
            >
              <i className="ti ti-file-text" aria-hidden="true" /> PDF
            </button>
          </div>

          <div className={styles.formGrid}>
            <div className={`${styles.field} ${styles.fullWidth}`}>
              <label className={styles.label}>Título del caso</label>
              <input
                className={styles.input}
                name="titulo"
                value={form.titulo}
                onChange={onChange}
                placeholder="Ej. Demanda por incumplimiento de contrato"
              />
              {fieldErrors.titulo && <span className={styles.fieldError}>{fieldErrors.titulo}</span>}
            </div>

            {modo === 'texto' ? (
              <div className={`${styles.field} ${styles.fullWidth}`}>
                <label className={styles.label}>Descripción del caso</label>
                <textarea
                  className={styles.textarea}
                  name="descripcion"
                  value={form.descripcion}
                  onChange={onChange}
                  placeholder="Describe los hechos, antecedentes y lo que buscas resolver..."
                />
                {fieldErrors.descripcion && <span className={styles.fieldError}>{fieldErrors.descripcion}</span>}
              </div>
            ) : (
              <div className={`${styles.field} ${styles.fullWidth}`}>
                <label className={styles.label}>Archivo PDF</label>
                <div
                  className={styles.dropzone}
                  onClick={() => fileInputRef.current?.click()}
                  role="button"
                  tabIndex={0}
                >
                  <i className={`ti ti-cloud-upload ${styles.dropzoneIcon}`} aria-hidden="true" />
                  {archivo ? (
                    <span className={styles.fileName}>
                      <i className="ti ti-file-text" aria-hidden="true" /> {archivo.name}
                    </span>
                  ) : (
                    <span>Haz clic para seleccionar un PDF</span>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf"
                  style={{ display: 'none' }}
                  onChange={(e) => onArchivoChange(e.target.files?.[0] ?? null)}
                />
                {fieldErrors.archivo && <span className={styles.fieldError}>{fieldErrors.archivo}</span>}

                <label className={styles.label} style={{ marginTop: 'var(--sp-3)' }}>
                  Notas adicionales (opcional)
                </label>
                <textarea
                  className={styles.textarea}
                  style={{ minHeight: 80 }}
                  name="descripcion"
                  value={form.descripcion}
                  onChange={onChange}
                  placeholder="Contexto adicional para el análisis..."
                />
              </div>
            )}
          </div>

          <div className={styles.submitRow}>
            <button type="button" className={styles.btnSecondary} onClick={() => navigate('/casos')} disabled={enviando}>
              Cancelar
            </button>
            <button type="submit" className={styles.btnPrimary} disabled={enviando}>
              {enviando ? 'Creando...' : 'Crear caso'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}