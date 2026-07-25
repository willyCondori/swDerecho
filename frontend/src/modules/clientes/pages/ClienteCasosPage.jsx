// modules/clientes/pages/ClienteCasosPage.jsx
import { useNavigate, useParams } from 'react-router-dom'
import useClienteCasos from '../hooks/useClienteCasos'
import styles from './ClienteCasosPage.module.css'

function getNombreCompleto(cliente) {
  if (!cliente) return ''
  const nombres = cliente.nombres ?? ''
  const apellidos = cliente.apellidos ?? ''
  return `${nombres} ${apellidos}`.trim() || `Cliente #${cliente.id}`
}

function EstadoBadge({ caso }) {
  if (caso.tiene_resultado) {
    return <span className={`${styles.badge} ${styles.badgeOk}`}>Análisis completo</span>
  }
  if (caso.tiene_documento) {
    return <span className={`${styles.badge} ${styles.badgePending}`}>PDF adjunto</span>
  }
  return <span className={`${styles.badge} ${styles.badgeMuted}`}>Sin analizar</span>
}

export default function ClienteCasosPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { cliente, casos, loading, error } = useClienteCasos(id)

  if (loading) {
    return <div className={styles.loaderWrap}>Cargando cliente...</div>
  }

  if (error && !cliente) {
    return (
      <div className={styles.root}>
        <div className={styles.errorBanner}>{error}</div>
        <button className={styles.btnSecondary} onClick={() => navigate('/clientes')}>
          Volver a clientes
        </button>
      </div>
    )
  }

  if (!cliente) return null

  return (
    <div className={styles.root}>
      <div className={styles.headerRow}>
        <button type="button" className={styles.backBtn} onClick={() => navigate('/clientes')} aria-label="Volver">
          <i className="ti ti-arrow-left" aria-hidden="true" />
        </button>
        <div className={styles.headerInfo}>
          <h1 className={styles.title}>{getNombreCompleto(cliente)}</h1>
          {cliente.telefono && <p className={styles.codigo}>{cliente.telefono}</p>}
        </div>
      </div>

      {error && <div className={styles.errorBanner}>{error}</div>}

      <div className={styles.card}>
        <h2 className={styles.cardTitle}>
          <i className="ti ti-briefcase" aria-hidden="true" /> Casos del cliente
        </h2>

        {casos.length === 0 ? (
          <p className={styles.emptyText}>Este cliente todavía no tiene casos registrados.</p>
        ) : (
          <ol className={styles.list}>
            {casos.map((caso) => (
              <li
                key={caso.id}
                className={styles.listItem}
                onClick={() => navigate(`/casos/${caso.id}`)}
              >
                <div className={styles.codigoRow}>
                  <span className={styles.codigo}>{caso.codigo}</span>
                  <EstadoBadge caso={caso} />
                </div>
                <p className={styles.descripcion}>{caso.titulo}</p>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  )
}