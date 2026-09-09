// modules/catalogo/components/articulos/FuenteInfo.jsx
import styles from '../../pages/articulos/CargaArticulosPage.module.css'

/**
 * Muestra el nivel de la jerarquía normativa elegida, como contexto para
 * el usuario mientras completa el formulario de carga.
 */
export default function FuenteInfo({ jerarquia }) {
  if (!jerarquia) return null

  return (
    <div className={styles.fuenteInfo}>
      <i className={`ti ti-info-circle ${styles.fuenteInfoIcon}`} aria-hidden="true" />
      <p className={styles.fuenteInfoText}>
        <strong>Jerarquía normativa: {jerarquia.nombre} (nivel {jerarquia.nivel})</strong>
        {' · '}
        Se asignará a este documento solo si todavía no tiene una jerarquía configurada.
      </p>
    </div>
  )
}
