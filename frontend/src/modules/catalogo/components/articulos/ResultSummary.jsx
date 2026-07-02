// modules/catalogo/components/articulos/ResultSummary.jsx
import styles from '../../pages/articulos/CargaArticulosPage.module.css'

export default function ResultSummary({ resumen, onReiniciar }) {
  return (
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
        <button className={styles.btnSecondary} onClick={onReiniciar}>
          <i className="ti ti-plus" aria-hidden="true" />
          Cargar otro documento
        </button>
      </div>
    </div>
  )
}