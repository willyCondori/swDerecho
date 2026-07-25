// modules/catalogo/components/articulos/JerarquiaBar.jsx
import styles from '../../pages/articulos/VerArticulos.module.css'

export default function JerarquiaBar({ valor }) {
  const pct = Math.round((valor ?? 0) * 100)
  return (
    <div className={styles.jerarquiaBar}>
      <div className={styles.jerarquiaTrack}>
        <div className={styles.jerarquiaFill} style={{ width: `${pct}%` }} />
      </div>
      <span className={styles.jerarquiaNum}>{(valor ?? 0).toFixed(1)}</span>
    </div>
  )
}