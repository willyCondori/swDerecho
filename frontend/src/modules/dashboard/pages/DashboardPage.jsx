// modules/dashboard/pages/DashboardPage.jsx
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../../auth/store/authStore'
import useCasos from '../hooks/useCasos'
import { computeCasoStats, getGreeting } from '../utils/dashboardUtils'
import MetricsGrid from '../components/MetricsGrid'
import CasosRecientesCard from '../components/CasosRecientesCard'
import ArticulosCard from '../components/ArticulosCard'
import PipelineCard from '../components/PipelineCard'
import AccesoRapidoCard from '../components/AccesoRapidoCard'
import styles from './DashboardPage.module.css'

// Pipeline IA — en producción vendría del estado Celery del último análisis
const PIPELINE_STATE = {
  chunking: 'done',
  embeddings: 'done',
  ranking: 'active',
  llm: 'waiting',
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const { casos, loading, error, reload } = useCasos({ pageSize: 20 })
  const stats = computeCasoStats(casos)

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

      <MetricsGrid loading={loading} stats={stats} />

      <div className={styles.mainGrid}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
          <CasosRecientesCard casos={casos} loading={loading} error={error} onRetry={reload} />
          <ArticulosCard />
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