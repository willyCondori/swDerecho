// modules/dashboard/components/AccesoRapidoCard.jsx
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../../auth/store/authStore'
import styles from '../pages/DashboardPage.module.css'
import { QUICK_ACCESS_ITEMS } from '../constants/dashboardConstants'

export default function AccesoRapidoCard() {
  const navigate = useNavigate()
  const esAdmin = useAuthStore((s) => s.isAdmin())
  const items = QUICK_ACCESS_ITEMS.filter((item) => !item.adminOnly || esAdmin)

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <h2 className={styles.cardTitle}>
          <i className={`ti ti-bolt ${styles.cardTitleIcon}`} aria-hidden="true" />
          Acceso rápido
        </h2>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
        {items.map((item) => (
          <button
            key={item.path}
            className={styles.btnSecondary}
            style={{ justifyContent: 'flex-start', width: '100%' }}
            onClick={() => navigate(item.path)}
          >
            <i className={`ti ${item.icon}`} aria-hidden="true" />
            {item.label}
          </button>
        ))}
      </div>
    </div>
  )
}