// modules/catalogo/components/articulos/ResultSummary.jsx
import AvisosVigencia from './AvisosVigencia'
import { useNavigate } from 'react-router-dom'
import styles from '../../pages/articulos/CargaArticulosPage.module.css'

export default function ResultSummary({ resumen, onReiniciar }) {
  const navigate = useNavigate()
  return (
    <div className={styles.resultCard}>
      <div className={styles.resultHeader}>
        <div className={styles.resultIcon}>
          <i className="ti ti-circle-check" aria-hidden="true" />
        </div>
        <div>
          <p className={styles.resultTitle}>Procesamiento completado</p>
          <p className={styles.resultSubtitle}>
            {resumen.norma} · {resumen.rama}
            {resumen.jerarquia && <> · {resumen.jerarquia}</>}
          </p>
        </div>
      </div>

      {resumen.normas_creadas?.length > 0 && <section role="status" aria-label="Normas nuevas creadas">
        <h3>Normas nuevas creadas ({resumen.normas_creadas.length})</h3>
        <ul>{resumen.normas_creadas.map((n) => <li key={n.id}>{n.nombre}</li>)}</ul>
      </section>}
      {resumen.normas_reutilizadas?.length > 0 && <p role="status">Normas existentes reutilizadas: {resumen.normas_reutilizadas.map((n) => n.nombre).join(', ')}. No se crearon normas nuevas en esta carga.</p>}
      {resumen.revision && <p className={styles.reviewSummary}>
        {resumen.revision.actualizar} artículos actualizados · {resumen.revision.nuevo} nuevos · {resumen.revision.sin_cambios || 0} sin cambios de texto ·
        {' '}{resumen.revision.retirados} retirados del catálogo activo ·
        {' '}{resumen.revision.derogados_indicados} con indicación de derogación o abrogación en el PDF.
      </p>}
      {resumen.revision?.disposiciones > 0 && <p>{resumen.revision.disposiciones} disposiciones guardadas en su tabla propia.</p>}
      {resumen.revision?.avisos?.length > 0 && <p>Los avisos siguientes documentan efectos detectados en la fuente. Subir este PDF no confirma automáticamente derogaciones ni abrogaciones.</p>}
      <AvisosVigencia avisos={resumen.revision?.avisos || []} />
      <div className={styles.statsGrid}>
        <div className={styles.statBox}>
          <p className={styles.statValue}>{resumen.total_encontrados}</p>
          <p className={styles.statLabel}>Artículos encontrados</p>
        </div>
        <div className={styles.statBox}>
          <p className={`${styles.statValue} ${styles.green}`}>{resumen.guardados}</p>
          <p className={styles.statLabel}>Artículos guardados</p>
        </div>
        <div className={styles.statBox}>
          <p className={styles.statValue}>{resumen.revision?.disposiciones || 0}</p>
          <p className={styles.statLabel}>Disposiciones guardadas</p>
        </div>
        <div className={styles.statBox}>
          <p className={styles.statValue}>{resumen.revision?.normas_guardadas ?? 1} de {resumen.revision?.normas_detectadas ?? 1}</p>
          <p className={styles.statLabel}>Normas del PDF procesadas en esta carga</p>
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
        <button className={styles.btnSecondary} onClick={onReiniciar}>
          <i className="ti ti-plus" aria-hidden="true" />
          Cargar otro documento
        </button>
        <button
          type="button"
          className={styles.btnPrimary}
          onClick={() => navigate('/catalogo/articulos')}
        >
          <i className="ti ti-list-details" aria-hidden="true" />
          Ver artículos
        </button>
      </div>
    </div>
  )
}
