// modules/dashboard/components/MetricCard.jsx
import styles from '../pages/DashboardPage.module.css'

export default function MetricCard({ label, value, icon, iconColorCls, delta, deltaCls = styles.neutral }) {
  return (
    <div className={styles.metricCard}>
      <div className={styles.metricTop}>
        <span className={styles.metricLabel}>{label}</span>
        <span className={`${styles.metricIcon} ${iconColorCls}`}>
          <i className={`ti ${icon}`} aria-hidden="true" />
        </span>
      </div>
      <span className={styles.metricValue}>{value}</span>
      <span className={`${styles.metricDelta} ${deltaCls}`}>{delta}</span>
    </div>
  )
}