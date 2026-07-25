// modules/catalogo/components/articulos/CatalogoHeader.jsx
import styles from '../../pages/articulos/VerArticulos.module.css'

export default function CatalogoHeader({ totalCount, onRecargar, onCargarPdf }) {
  return (
    <header className={styles.header}>
      <div className={styles.headerLeft}>
        <h1 className={styles.title}>Catálogo de artículos</h1>
        <p className={styles.subtitle}>
          {totalCount > 0
            ? `${totalCount.toLocaleString('es-BO')} artículos jurídicos bolivianos indexados`
            : 'Artículos jurídicos bolivianos'}
        </p>
      </div>
      <div className={styles.headerRight}>
        <button className={styles.btnSecondary} onClick={onRecargar} title="Recargar">
          <i className="ti ti-refresh" aria-hidden="true" />
          Recargar
        </button>
        <button className={styles.btnPrimary} onClick={onCargarPdf}>
          <i className="ti ti-file-upload" aria-hidden="true" />
          Cargar PDF
        </button>
      </div>
    </header>
  )
}