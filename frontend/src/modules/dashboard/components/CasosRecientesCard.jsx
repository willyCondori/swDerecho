// modules/dashboard/components/CasosRecientesCard.jsx
import { useNavigate } from 'react-router-dom'
import styles from '../pages/DashboardPage.module.css'
import { getEstadoBadge, getBorderClass, formatFecha } from '../utils/dashboardUtils'

function CaseItem({ caso, onOpen }) {
  const estado = getEstadoBadge(caso)
  return (
    <div
      className={`${styles.caseItem} ${getBorderClass(caso)}`}
      onClick={() => onOpen(caso.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onOpen(caso.id)}
      aria-label={`Ver caso ${caso.codigo}`}
    >
      <div className={styles.caseItemLeft}>
        <span className={styles.caseCodigo}>{caso.codigo} · {caso.titulo}</span>
        <span className={styles.caseInfo}>
          {caso.cliente_nombre} · {formatFecha(caso.created_at)}
        </span>
      </div>
      <span className={`${styles.badge} ${estado.cls}`}>{estado.label}</span>
    </div>
  )
}

export default function CasosRecientesCard({ casos, loading, error, onRetry }) {
  const navigate = useNavigate()
  const casoRecientes = casos.slice(0, 5)

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <h2 className={styles.cardTitle}>
          <i className={`ti ti-folder ${styles.cardTitleIcon}`} aria-hidden="true" />
          Casos recientes
        </h2>
        <button className={styles.cardLink} onClick={() => navigate('/casos')}>
          Ver todos →
        </button>
      </div>

      {loading ? (
        <div className={styles.caseList}>
          {[1, 2, 3].map((k) => (
            <div key={k} className={`${styles.skeleton} ${styles.skeletonBlock}`} style={{ height: 58 }} />
          ))}
        </div>
      ) : error ? (
        <div className={styles.emptyState}>
          <i className={`ti ti-wifi-off ${styles.emptyIcon}`} aria-hidden="true" />
          <p className={styles.emptyText}>{error}</p>
          <button className={styles.btnSecondary} onClick={onRetry}>
            Reintentar
          </button>
        </div>
      ) : casoRecientes.length === 0 ? (
        <div className={styles.emptyState}>
          <i className={`ti ti-folder-off ${styles.emptyIcon}`} aria-hidden="true" />
          <p className={styles.emptyText}>Sin casos registrados aún.</p>
          <button className={styles.btnPrimary} onClick={() => navigate('/casos/nuevo')}>
            <i className="ti ti-plus" aria-hidden="true" /> Crear primer caso
          </button>
        </div>
      ) : (
        <div className={styles.caseList}>
          {casoRecientes.map((caso) => (
            <CaseItem key={caso.id} caso={caso} onOpen={(id) => navigate(`/casos/${id}`)} />
          ))}
        </div>
      )}
    </div>
  )
}