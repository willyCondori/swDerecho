import { useNavigate, useParams } from 'react-router-dom'
import useEditarCaso from '../hooks/useEditarCaso'
import styles from './EditarCasoPage.module.css'

export default function EditarCasoPage() {
  const { id } = useParams()
  const navigate = useNavigate()

  const {
    form, fieldErrors, loading, guardando, error,
    casoOriginal, onChange, onSubmit,
  } = useEditarCaso(id)

  if (loading) {
    return <div className={styles.loaderWrap}>Cargando caso...</div>
  }

  if (error && !casoOriginal) {
    return (
      <div className={styles.root}>
        <div className={styles.errorBanner}>{error}</div>
        <button className={styles.btnSecondary} onClick={() => navigate('/casos')}>
          Volver a casos
        </button>
      </div>
    )
  }

  if (!casoOriginal) return null

  return (
    <div className={styles.root}>
      <div className={styles.headerRow}>
        <button
          type="button"
          className={styles.backBtn}
          onClick={() => navigate(`/casos/${id}`)}
          aria-label="Volver"
        >
          <i className="ti ti-arrow-left" aria-hidden="true" />
        </button>
        <div>
          <h1 className={styles.title}>Editar caso</h1>
          <p className={styles.subtitle}>
            <span className={styles.codigo}>{casoOriginal.codigo}</span> — actualiza el
            título, la descripción o el estado del caso.
          </p>
        </div>
      </div>

      {error && <div className={styles.errorBanner}>{error}</div>}

      <form onSubmit={onSubmit} noValidate>
        <div className={styles.card}>
          <h2 className={styles.cardTitle}>
            <i className="ti ti-briefcase" aria-hidden="true" /> Datos del caso
          </h2>

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

            <div className={`${styles.field} ${styles.fullWidth}`}>
              <label className={styles.label}>Descripción del caso</label>
              <textarea
                className={styles.textarea}
                name="descripcion"
                value={form.descripcion}
                onChange={onChange}
                placeholder="Describe los hechos, antecedentes y lo que buscas resolver..."
              />
              {fieldErrors.descripcion && (
                <span className={styles.fieldError}>{fieldErrors.descripcion}</span>
              )}
              {!form.descripcion.trim() && (
                <span className={styles.hintText}>
                  Podés dejar esto vacío si el caso se maneja con el PDF adjunto.
                </span>
              )}
            </div>
          </div>

          <div className={styles.checkboxRow}>
            <input
              id="estado"
              name="estado"
              type="checkbox"
              className={styles.checkbox}
              checked={form.estado}
              onChange={onChange}
            />
            <label htmlFor="estado" className={styles.checkboxLabel}>
              <strong>Caso activo.</strong> Si lo desmarcás, el caso pasa a inactivo y
              deja de aparecer en los listados normales (podés reactivarlo después
              volviendo a marcar esta opción).
            </label>
          </div>

          {/* Datos de solo lectura, para contexto — no editables acá */}
          <div className={styles.readonlyBlock}>
            <div className={styles.readonlyItem}>
              <span className={styles.readonlyLabel}>Cliente</span>
              <span className={styles.readonlyValue}>
                {casoOriginal.cliente?.nombre_completo || `Cliente #${casoOriginal.cliente?.id ?? '—'}`}
              </span>
            </div>
            {casoOriginal.rama_detectada && (
              <div className={styles.readonlyItem}>
                <span className={styles.readonlyLabel}>Rama detectada</span>
                <span className={styles.readonlyValue}>{casoOriginal.rama_detectada}</span>
              </div>
            )}
            <p className={styles.hintText}>
              El cliente y la rama del derecho no se editan desde acá. La rama se
              detecta automáticamente al analizar el caso con IA.
            </p>
          </div>

          <div className={styles.submitRow}>
            <button
              type="button"
              className={styles.btnSecondary}
              onClick={() => navigate(`/casos/${id}`)}
              disabled={guardando}
            >
              Cancelar
            </button>
            <button type="submit" className={styles.btnPrimary} disabled={guardando}>
              {guardando ? 'Guardando...' : 'Guardar cambios'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}