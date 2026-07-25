// modules/dashboard/components/PipelineCard.jsx
import { useNavigate } from 'react-router-dom'
import styles from '../pages/DashboardPage.module.css'
import { PIPELINE_STEPS, PIPELINE_WIDTH } from '../constants/dashboardConstants'

const STATUS_LABEL = {
  done: 'OK',
  active: 'En proceso',
  waiting: 'Esperando',
}

export default function PipelineCard({ pipelineState }) {
  const navigate = useNavigate()

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <h2 className={styles.cardTitle}>
          <i className={`ti ti-cpu ${styles.cardTitleIcon}`} aria-hidden="true" />
          Pipeline IA
        </h2>
        <button className={styles.cardLink} onClick={() => navigate('/ia')}>
          Detalles →
        </button>
      </div>
      <div className={styles.pipelineList}>
        {PIPELINE_STEPS.map((step) => {
          const state = pipelineState[step.key]
          return (
            <div key={step.key} className={styles.pipelineStep}>
              <div className={`${styles.pipelineIcon} ${styles[state]}`}>
                <i className={`ti ${step.icon}`} aria-hidden="true" />
              </div>
              <div className={styles.pipelineBody}>
                <div className={styles.pipelineLabel}>
                  <span className={styles.pipelineStepName}>{step.label}</span>
                  <span className={`${styles.pipelineStatus} ${styles[state]}`}>
                    {STATUS_LABEL[state]}
                  </span>
                </div>
                <div className={styles.pipelineBar}>
                  <div
                    className={`${styles.pipelineProgress} ${styles[state]}`}
                    style={{ width: PIPELINE_WIDTH[state] }}
                  />
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}