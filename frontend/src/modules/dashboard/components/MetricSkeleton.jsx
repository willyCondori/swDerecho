// modules/dashboard/components/MetricSkeleton.jsx
import styles from '../pages/DashboardPage.module.css'

export default function MetricSkeleton() {
  return (
    <div className={styles.metricCard}>
      <div className={styles.metricTop}>
        <div className={`${styles.skeleton} ${styles.skeletonText}`} style={{ width: 80 }} />
        <div className={styles.skeleton} style={{ width: 30, height: 30, borderRadius: 6 }} />
      </div>
      <div className={`${styles.skeleton} ${styles.skeletonBlock}`} style={{ width: 60, height: 36 }} />
      <div className={`${styles.skeleton} ${styles.skeletonText}`} style={{ width: 100 }} />
    </div>
  )
}