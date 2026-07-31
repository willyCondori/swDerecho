// modules/dashboard/components/MetricsGrid.jsx
import styles from '../pages/DashboardPage.module.css'
import MetricCard from './MetricCard'
import MetricSkeleton from './MetricSkeleton'

export default function MetricsGrid({ loading, stats }) {
  const { total, completos, conPdf, pendientes } = stats

  return (
    <section aria-label="Resumen de métricas">
      <div className={styles.metricsGrid}>
        {loading ? (
          [1, 2, 3, 4].map((k) => <MetricSkeleton key={k} />)
        ) : (
          <>
            <MetricCard
              label="Casos activos"
              value={total}
              icon="ti-folder"
              iconColorCls={styles.purple}
              delta={<><i className="ti ti-arrow-up" aria-hidden="true" /> {completos} completados</>}
              deltaCls={styles.up}
            />
            <MetricCard
              label="Análisis IA"
              value={completos}
              icon="ti-cpu"
              iconColorCls={styles.green}
              delta="Procesados"
            />
            <MetricCard
              label="Con PDF"
              value={conPdf}
              icon="ti-file-text"
              iconColorCls={styles.amber}
              delta="Documentos subidos"
            />
            <MetricCard
              label="Pendientes"
              value={pendientes}
              icon="ti-clock"
              iconColorCls={styles.blue}
              delta={pendientes > 0 ? 'Requieren análisis' : 'Todo al día'}
              deltaCls={pendientes > 0 ? styles.down : styles.neutral}
            />
          </>
        )}
      </div>
    </section>
  )
}