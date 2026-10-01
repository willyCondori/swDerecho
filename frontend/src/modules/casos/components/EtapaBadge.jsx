// modules/casos/components/EtapaBadge.jsx
import { varianteEtapa } from '../utils/etapas'
import styles from './Seguimiento.module.css'

const CLASE_POR_VARIANTE = {
  muted: styles.badgeMuted,
  purple: styles.badgePurple,
  ok: styles.badgeOk,
}

export default function EtapaBadge({ etapa, label }) {
  if (!etapa) return null
  return (
    <span className={`${styles.badge} ${CLASE_POR_VARIANTE[varianteEtapa(etapa)]}`}>
      <i className="ti ti-route" aria-hidden="true" />
      {label || etapa}
    </span>
  )
}
