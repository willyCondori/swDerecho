// modules/casos/pages/SeguimientoCasoPage.jsx
// Historial de seguimiento de un caso: la línea de tiempo completa y,
// para quien puede escribir, el formulario para avanzar de etapa. Vive
// en su propia URL (/casos/:id/seguimiento) en vez de ir directo en el
// detalle del caso, que ya tiene bastante contenido.
import { useNavigate, useParams } from 'react-router-dom'
import useSeguimientoCaso from '../hooks/useSeguimientoCaso'
import useEtapasCaso from '../hooks/useEtapasCaso'
import EtapaBadge from '../components/EtapaBadge'
import SeguimientoTimeline from '../components/SeguimientoTimeline'
import CambiarEtapaForm from '../components/CambiarEtapaForm'
import { formatFechaHora } from '../utils/etapas'
import seguimientoStyles from '../components/Seguimiento.module.css'
import useAuthStore from '../../auth/store/authStore'
import styles from './CasoDetailPage.module.css'

export default function SeguimientoCasoPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const puedeEscribir = useAuthStore((s) => s.puedeEscribir())
  const { caso, seguimientos, loading, error, guardandoEtapa, cambiarEtapa } = useSeguimientoCaso(id)
  const etapas = useEtapasCaso(puedeEscribir)

  if (loading) {
    return <div className={styles.loaderWrap}>Cargando seguimiento...</div>
  }

  if (error && !caso) {
    return (
      <div className={styles.root}>
        <div className={styles.errorBanner}>{error}</div>
        <button className={styles.btnSecondary} onClick={() => navigate('/casos')}>
          Volver a casos
        </button>
      </div>
    )
  }

  if (!caso) return null

  return (
    <div className={styles.root}>
      <div className={styles.headerRow}>
        <button
          type="button"
          className={styles.backBtn}
          onClick={() => navigate(`/casos/${id}`)}
          aria-label="Volver al caso"
        >
          <i className="ti ti-arrow-left" aria-hidden="true" />
        </button>
        <div className={styles.headerInfo}>
          <span className={styles.codigo}>{caso.codigo}</span>
          <h1 className={styles.title}>Seguimiento — {caso.titulo}</h1>
        </div>
      </div>

      {error && <div className={styles.errorBanner}>{error}</div>}

      <div className={styles.grid}>
        <div className={styles.mainCol}>
          <div className={styles.card}>
            <h2 className={styles.cardTitle}>
              <i className="ti ti-timeline" aria-hidden="true" /> Línea de tiempo
            </h2>
            <SeguimientoTimeline seguimientos={seguimientos} />
          </div>
        </div>

        <div className={styles.sideCol}>
          <div className={styles.card}>
            <h2 className={styles.cardTitle}>
              <i className="ti ti-route" aria-hidden="true" /> Etapa actual
            </h2>
            <div className={seguimientoStyles.etapaActual}>
              <EtapaBadge etapa={caso.etapa} label={caso.etapa_display} />
              {caso.etapa_actualizada_at && (
                <p className={seguimientoStyles.etapaFecha}>
                  Actualizada el {formatFechaHora(caso.etapa_actualizada_at)}
                </p>
              )}
            </div>
            {puedeEscribir && (
              <CambiarEtapaForm
                etapas={etapas}
                etapaActual={caso.etapa}
                guardando={guardandoEtapa}
                onSubmit={cambiarEtapa}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
