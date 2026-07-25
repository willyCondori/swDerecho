// modules/catalogo/components/articulos/StatsRow.jsx
import styles from '../../pages/articulos/VerArticulos.module.css'

export default function StatsRow({ totalCount, totalNormas, totalRamas, pageSize, mostrarPageSize }) {
  return (
    <div className={styles.statsRow}>
      <div className={styles.statPill}>
        <div className={`${styles.statPillIcon} ${styles.purple}`}>
          <i className="ti ti-article" aria-hidden="true" />
        </div>
        <div className={styles.statPillBody}>
          <p className={styles.statPillValue}>{totalCount.toLocaleString('es-BO')}</p>
          <p className={styles.statPillLabel}>Total artículos</p>
        </div>
      </div>

      <div className={styles.statPill}>
        <div className={`${styles.statPillIcon} ${styles.blue}`}>
          <i className="ti ti-building-bank" aria-hidden="true" />
        </div>
        <div className={styles.statPillBody}>
          <p className={styles.statPillValue}>{totalNormas}</p>
          <p className={styles.statPillLabel}>Normas</p>
        </div>
      </div>

      <div className={styles.statPill}>
        <div className={`${styles.statPillIcon} ${styles.green}`}>
          <i className="ti ti-git-branch" aria-hidden="true" />
        </div>
        <div className={styles.statPillBody}>
          <p className={styles.statPillValue}>{totalRamas}</p>
          <p className={styles.statPillLabel}>Ramas</p>
        </div>
      </div>

      {mostrarPageSize && (
        <div className={styles.statPill}>
          <div className={`${styles.statPillIcon} ${styles.amber}`}>
            <i className="ti ti-filter" aria-hidden="true" />
          </div>
          <div className={styles.statPillBody}>
            <p className={styles.statPillValue}>{pageSize}</p>
            <p className={styles.statPillLabel}>Por página</p>
          </div>
        </div>
      )}
    </div>
  )
}