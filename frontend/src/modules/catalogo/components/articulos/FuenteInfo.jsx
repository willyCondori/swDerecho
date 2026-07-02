// modules/catalogo/components/articulos/FuenteInfo.jsx
import styles from '../../pages/articulos/CargaArticulosPage.module.css'

export default function FuenteInfo({ fuente }) {
  if (!fuente) return null

  return (
    <div className={styles.fuenteInfo}>
      <i className={`ti ti-info-circle ${styles.fuenteInfoIcon}`} aria-hidden="true" />
      <p className={styles.fuenteInfoText}>
        {fuente.descripcion}
        {' · '}
        <strong>Jerarquía normativa: {fuente.jerarquia}</strong>
        {fuente.esperados && (
          <> · Aprox. {fuente.esperados} artículos esperados</>
        )}
      </p>
    </div>
  )
}