// modules/catalogo/components/articulos/JerarquiaNivel.jsx
import styles from '../../pages/articulos/VerArticulos.module.css'

// Jerarquía normativa de un artículo: solo el nombre y el nivel, por ejemplo
// "Ley (2)". A menor nivel, mayor jerarquía (1 Constitución · 2 Ley · ...).
export default function JerarquiaNivel({ nivel, nombre }) {
  if (nivel == null) {
    return <span className={styles.jerarquiaNum}>—</span>
  }

  return (
    <span className={styles.jerarquiaNum} title={nombre || `Nivel ${nivel}`}>
      {nombre ? `${nombre} (${nivel})` : nivel}
    </span>
  )
}
