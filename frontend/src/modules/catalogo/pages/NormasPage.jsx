// modules/catalogo/pages/NormasPage.jsx
import NormasSection from '../components/administrar/NormasSection'
import styles from './AdministrarCatalogoPage.module.css'

export default function NormasPage() {
  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Normas</h1>
          <p className={styles.subtitle}>
            Elimina una norma para ocultarla del catálogo y del análisis de
            casos, o recupérala desde la pestaña "Eliminadas". Al eliminarla
            no se borra nada: sus artículos se conservan y vuelven a estar
            disponibles cuando la recuperas.
          </p>
        </div>
      </header>

      <NormasSection />
    </div>
  )
}
