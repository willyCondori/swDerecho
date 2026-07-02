// modules/catalogo/components/articulos/ProgressPanel.jsx
import styles from '../../pages/articulos/CargaArticulosPage.module.css'

export default function ProgressPanel({ paso, progreso }) {
  return (
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
  )
}