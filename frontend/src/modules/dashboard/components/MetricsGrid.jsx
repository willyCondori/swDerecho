// modules/dashboard/components/MetricsGrid.jsx
import styles from '../pages/DashboardPage.module.css'
import MetricCard from './MetricCard'
import MetricSkeleton from './MetricSkeleton'

// `stats` viene de GET /api/dashboard/resumen/ (ver useDashboardResumen):
// totales reales del bufete (o de "mis casos" para un Asistente), no una
// muestra de los primeros 20 casos como antes.
export default function MetricsGrid({ loading, stats }) {
  const { totales = {}, estado_analisis = [] } = stats

  const porEstado = Object.fromEntries(
    estado_analisis.map((e) => [e.estado, e.cantidad])
  )
  const completados = porEstado.completado ?? 0
  const procesando  = porEstado.procesando ?? 0
  const pendientes  = porEstado.pendiente ?? 0
  const conError    = porEstado.error ?? 0

  return (
    <section aria-label="Resumen de métricas">
      <div className={styles.metricsGrid}>
        {loading ? (
          [1, 2, 3, 4].map((k) => <MetricSkeleton key={k} />)
        ) : (
          <>
            <MetricCard
              label="Casos activos"
              value={totales.casos_activos ?? 0}
              icon="ti-folder"
              iconColorCls={styles.purple}
              delta={`${totales.casos_en_papelera ?? 0} en papelera`}
            />
            <MetricCard
              label="Análisis completados"
              value={completados}
              icon="ti-cpu"
              iconColorCls={styles.green}
              delta="Procesados"
            />
            <MetricCard
              label="En proceso"
              value={procesando}
              icon="ti-loader-2"
              iconColorCls={styles.amber}
              delta="Analizando ahora"
            />
            <MetricCard
              label="Pendientes"
              value={pendientes}
              icon="ti-clock"
              iconColorCls={styles.blue}
              delta={conError > 0 ? `${conError} con error` : 'Todo al día'}
              deltaCls={conError > 0 ? styles.down : styles.neutral}
            />
          </>
        )}
      </div>
    </section>
  )
}