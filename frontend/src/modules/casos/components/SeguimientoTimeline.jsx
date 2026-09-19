// modules/casos/components/SeguimientoTimeline.jsx
import { formatFechaHora } from '../utils/etapas'
import styles from './Seguimiento.module.css'

// `seguimientos` llega del backend ordenado del más reciente al más
// antiguo; el primero es el estado actual del caso.
export default function SeguimientoTimeline({ seguimientos }) {
  if (!seguimientos?.length) {
    return <p className={styles.emptyText}>Este caso todavía no tiene movimientos de seguimiento.</p>
  }

  return (
    <ol className={styles.timeline}>
      {seguimientos.map((s, i) => {
        const cambioDeEtapa = s.etapa_anterior && s.etapa_anterior !== s.etapa
        return (
          <li key={s.id} className={`${styles.item} ${i === 0 ? styles.itemActual : ''}`}>
            <span className={styles.dot} aria-hidden="true" />
            <div className={styles.itemHeader}>
              <span className={styles.itemEtapa}>{s.etapa_display}</span>
              {cambioDeEtapa && (
                <span className={styles.itemDesde}>desde {s.etapa_anterior_display}</span>
              )}
            </div>
            <p className={styles.itemMeta}>
              {formatFechaHora(s.created_at)} · {s.usuario_nombre}
            </p>
            {s.nota && <p className={styles.itemNota}>{s.nota}</p>}
          </li>
        )
      })}
    </ol>
  )
}
