import { useId, useState } from 'react'
import styles from '../pages/CasoDetailPage.module.css'

export default function BloquePlegable({ titulo, icono, nivel = 2, abiertoInicial = true, className = styles.card, children }) {
  const [abierto, setAbierto] = useState(abiertoInicial)
  const contenidoId = useId()
  const Titulo = `h${nivel}`
  return <section className={className} aria-label={titulo}>
    <div className={styles.bloqueHeader}>
      <Titulo className={styles.bloqueTitulo}>
        {icono && <i className={`ti ${icono}`} aria-hidden="true" />} {titulo}
      </Titulo>
      <button type="button" className={`${styles.btnSecondary} ${styles.bloqueToggle}`}
        aria-expanded={abierto} aria-controls={contenidoId}
        aria-label={`${abierto ? 'Ocultar' : 'Mostrar'} ${titulo}`}
        onClick={() => setAbierto(valor => !valor)}>
        {abierto ? 'Ocultar' : 'Mostrar'}
        <i className={`ti ${abierto ? 'ti-chevron-up' : 'ti-chevron-down'}`} aria-hidden="true" />
      </button>
    </div>
    <div id={contenidoId} hidden={!abierto}>{children}</div>
  </section>
}
