// modules/dashboard/components/ArticulosCard.jsx
import { useNavigate } from 'react-router-dom'
import styles from '../pages/DashboardPage.module.css'

// `articulos` viene de normas_mas_consultadas en GET /api/dashboard/resumen/:
// [{ articulo_id, numero_articulo, norma, frecuencia }], ya ordenado por
// frecuencia_historica descendente (se incrementa cada vez que el artículo
// queda seleccionado en el resultado de un análisis). El ancho de la barra
// se calcula acá, relativo al más frecuente de la lista.
export default function ArticulosCard({ articulos = [], loading = false }) {
  const navigate = useNavigate()
  const maxFrecuencia = articulos.length ? articulos[0].frecuencia : 0

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
      {!loading && articulos.length === 0 ? (
        <div className={styles.emptyState}>
          <i className={`ti ti-chart-bar-off ${styles.emptyIcon}`} aria-hidden="true" />
          <p className={styles.emptyText}>
            Todavía no hay suficientes análisis completados para mostrar esto.
          </p>
        </div>
      ) : (
        <div className={styles.articuloList}>
          {articulos.map((art) => (
            <div key={art.articulo_id} className={styles.articuloItem}>
              <div className={styles.articuloBody}>
                <div className={styles.articuloHeader}>
                  <span className={styles.articuloNombre}>
                    Art. {art.numero_articulo} — {art.norma}
                  </span>
                  <span className={styles.articuloCount}>{art.frecuencia}</span>
                </div>
                <div className={styles.articuloBarBg}>
                  <div
                    className={styles.articuloBar}
                    style={{ width: `${maxFrecuencia ? (art.frecuencia / maxFrecuencia) * 100 : 0}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}