// modules/dashboard/pages/DashboardPage.jsx
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../../auth/store/authStore'
import useCasos from '../hooks/useCasos'
import useDashboardResumen from '../hooks/useDashboardResumen'
import { getGreeting } from '../utils/dashboardUtils'
import MetricsGrid from '../components/MetricsGrid'
import CasosRecientesCard from '../components/CasosRecientesCard'
import ArticulosCard from '../components/ArticulosCard'
import styles from './DashboardPage.module.css'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  // Casos recientes: sigue usando la muestra paginada, porque acá sí
  // interesa el detalle de los últimos casos, no un agregado.
  const { casos, loading, error, reload } = useCasos({ pageSize: 20 })
  // Métricas y "artículos más aplicados": vienen agregadas del backend
  // completo (GET /api/dashboard/resumen/), no de esta misma muestra de 20.
  const { resumen, loading: loadingResumen } = useDashboardResumen()

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <p className={styles.greeting}>{getGreeting()}, sistema activo</p>
          <h1 className={styles.title}>Panel de control</h1>
          <p className={styles.subtitle}>
            {new Date().toLocaleDateString('es-BO', {
              weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
            })}
          </p>
        </div>
        <div className={styles.headerActions}>
          <button className={styles.btnSecondary} onClick={() => navigate('/casos')}>
            <i className="ti ti-folder" aria-hidden="true" />
            Ver casos
          </button>
          <button className={styles.btnPrimary} onClick={() => navigate('/casos/nuevo')}>
            <i className="ti ti-plus" aria-hidden="true" />
            Nuevo caso
          </button>
        </div>
      </header>

      <MetricsGrid loading={loadingResumen} stats={resumen} />

      <div className={styles.mainGrid}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
          <CasosRecientesCard casos={casos} loading={loading} error={error} onRetry={reload} />
          <ArticulosCard articulos={resumen.normas_mas_consultadas} loading={loadingResumen} />
        </div>
{/* 
<div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
  <PipelineCard pipelineState={PIPELINE_STATE} />
  <AccesoRapidoCard />
</div>
*/}

      </div>
    </div>
  )
}