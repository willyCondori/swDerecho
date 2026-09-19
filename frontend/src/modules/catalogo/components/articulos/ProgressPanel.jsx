// modules/catalogo/components/articulos/ProgressPanel.jsx
import styles from '../../pages/articulos/CargaArticulosPage.module.css'

export default function ProgressPanel({ paso, progreso, documento, retomada = false }) {
  return (
    <div className={styles.progressCard} role="status" aria-live="polite">
      <div className={styles.progressHeader}>
        <div className={`${styles.progressIcon} ${styles.spinning}`}>
          <i className="ti ti-loader-2" aria-hidden="true" />
        </div>
        <div>
          <p className={styles.progressTitle}>
            {documento ? `Procesando «${documento}»...` : 'Procesando documento...'}
          </p>
          <p className={styles.progressStep}>{paso || 'Iniciando...'}</p>
        </div>
      </div>
      <div className={styles.progressBarBg}>
        <div className={styles.progressBar} style={{ width: `${progreso}%` }} />
      </div>
      <p className={styles.progressPercent}>{progreso}%</p>
      <p className={styles.progressHint}>
        <i className="ti ti-info-circle" aria-hidden="true" />{' '}
        {retomada
          ? 'Esta carga ya estaba en curso: retomamos su avance. '
          : ''}
        Puedes salir de esta pantalla; la carga sigue en el servidor y al volver verás su avance.
      </p>
    </div>
  )
}
