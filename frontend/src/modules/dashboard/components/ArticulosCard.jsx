// modules/dashboard/components/ArticulosCard.jsx
import { useNavigate } from 'react-router-dom'
import styles from '../pages/DashboardPage.module.css'
import { TOP_ARTICULOS_MOCK } from '../constants/dashboardConstants'

export default function ArticulosCard({ articulos = TOP_ARTICULOS_MOCK }) {
  const navigate = useNavigate()

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <h2 className={styles.cardTitle}>
          <i className={`ti ti-award ${styles.cardTitleIcon}`} aria-hidden="true" />
          Artículos más aplicados
        </h2>
        <button className={styles.cardLink} onClick={() => navigate('/catalogo')}>
          Ver catálogo →
        </button>
      </div>
      <div className={styles.articuloList}>
        {articulos.map((art) => (
          <div key={art.numero} className={styles.articuloItem}>
            <div className={styles.articuloBody}>
              <div className={styles.articuloHeader}>
                <span className={styles.articuloNombre}>{art.numero} — {art.titulo}</span>
                <span className={styles.articuloCount}>{art.count}</span>
              </div>
              <div className={styles.articuloBarBg}>
                <div className={styles.articuloBar} style={{ width: `${art.pct}%` }} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}