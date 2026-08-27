// modules/catalogo/components/articulos/JerarquiaBar.jsx
import styles from '../../pages/articulos/VerArticulos.module.css'

// Escala fija de jerarquía normativa (modulo_catalogo.models.jerarquia):
//   1 Constitución · 2 Ley · 3 Ley Departamental · 4 Ley Municipal
//   5 Decreto Supremo · 6 Decreto Departamental · 7 Decreto Municipal
//   8 Reglamento · 9 Resolución Suprema · 10 Resolución Ministerial
// A menor nivel, mayor jerarquía (la barra se llena más).
const NIVEL_MIN = 1
const NIVEL_MAX = 10

export default function JerarquiaBar({ nivel, nombre }) {
  if (nivel == null) {
    return (
      <div className={styles.jerarquiaBar}>
        <div className={styles.jerarquiaTrack}>
          <div className={styles.jerarquiaFill} style={{ width: '0%' }} />
        </div>
        <span className={styles.jerarquiaNum}>—</span>
      </div>
    )
  }

  const pct = Math.round(((NIVEL_MAX - nivel) / (NIVEL_MAX - NIVEL_MIN)) * 100)

  return (
    <div className={styles.jerarquiaBar} title={nombre || `Nivel ${nivel}`}>
      <div className={styles.jerarquiaTrack}>
        <div className={styles.jerarquiaFill} style={{ width: `${pct}%` }} />
      </div>
      <span className={styles.jerarquiaNum}>
        {nombre ? `${nombre} (${nivel})` : nivel}
      </span>
    </div>
  )
}