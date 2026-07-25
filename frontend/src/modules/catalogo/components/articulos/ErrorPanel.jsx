// modules/catalogo/components/articulos/ErrorPanel.jsx
import styles from '../../pages/articulos/CargaArticulosPage.module.css'

export default function ErrorPanel({ mensaje, onReintentar }) {
  return (
    <div className={styles.errorCard}>
      <div className={styles.errorCardIcon}>
        <i className="ti ti-alert-triangle" aria-hidden="true" />
      </div>
      <div style={{ flex: 1 }}>
        <p className={styles.errorCardTitle}>No se pudo completar la carga</p>
        <p className={styles.errorCardText}>{mensaje}</p>
        <div className={styles.resultActions} style={{ marginTop: 16 }}>
          <button className={styles.btnSecondary} onClick={onReintentar}>
            Reintentar
          </button>
        </div>
      </div>
    </div>
  )
}