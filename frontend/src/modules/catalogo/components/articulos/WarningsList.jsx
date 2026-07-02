// modules/catalogo/components/articulos/WarningsList.jsx
import styles from '../../pages/articulos/CargaArticulosPage.module.css'

export default function WarningsList({ advertencias }) {
  if (!advertencias?.length) return null

  return (
    <>
      {advertencias.map((aviso, i) => (
        <div key={i} className={styles.warningBox}>
          <i className={`ti ti-alert-triangle ${styles.warningIcon}`} aria-hidden="true" />
          <p className={styles.warningText}>{aviso}</p>
        </div>
      ))}
    </>
  )
}