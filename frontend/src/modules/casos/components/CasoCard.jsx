// modules/casos/components/CasoCard.jsx
import styles from '../pages/CasosPage.module.css'
import EtapaBadge from './EtapaBadge'

function getClienteNombre(caso) {
  // Listado: CasoListSerializer ya manda el nombre armado como string plano
  if (caso.cliente_nombre) return caso.cliente_nombre

  const cliente = caso.cliente
  if (!cliente) return 'Sin cliente asignado'
  if (typeof cliente === 'string') return cliente
  if (cliente.nombre_completo) return cliente.nombre_completo
  const nombres = cliente.nombres ?? ''
  const apellidos = cliente.apellidos ?? ''
  const completo = `${nombres} ${apellidos}`.trim()
  return completo || `Cliente #${cliente.id ?? caso.cliente_id ?? ''}`
}

function formatFecha(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('es-BO', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function CasoCard({ caso, onVerDetalle, onEliminar, eliminando = false, eliminarDeshabilitado = false }) {
  const tienePdf = caso.tiene_documento ?? caso.tiene_pdf ?? false

  return (
    <div className={styles.casoCard} onClick={() => onVerDetalle(caso.id)} role="button" tabIndex={0}
      aria-label={`Ver caso ${caso.titulo}`}
      onKeyDown={(e) => {
        if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          onVerDetalle(caso.id)
        }
      }}>
      <div className={styles.casoTop}>
        <div>
          <div className={styles.casoCodigo}>{caso.codigo}</div>
          <h3 className={styles.casoTitulo}>{caso.titulo}</h3>
        </div>
        <span className={`${styles.badge} ${tienePdf ? styles.badgePdf : styles.badgeSinPdf}`}>
          <i className="ti ti-file-text" aria-hidden="true" />
          {tienePdf ? 'PDF' : 'Sin PDF'}
        </span>
      </div>

      <div className={styles.casoCliente}>
        <i className="ti ti-user" aria-hidden="true" />
        {getClienteNombre(caso)}
      </div>

      <div className={styles.casoEtapa}>
        <EtapaBadge etapa={caso.etapa} label={caso.etapa_display} />
      </div>

      <div className={styles.casoFooter}>
        <span className={styles.casoFecha}>{formatFecha(caso.created_at)}</span>
        <div className={styles.casoAcciones}>
        {onEliminar && <button type="button" className={styles.eliminarBtn}
          title="Enviar a la papelera" aria-label={`Eliminar caso ${caso.titulo}`}
          disabled={eliminarDeshabilitado} aria-busy={eliminando}
          onClick={(e) => { e.stopPropagation(); onEliminar(caso) }}>
          <i className="ti ti-trash" aria-hidden="true" />
          {eliminando ? 'Eliminando…' : 'Eliminar'}
        </button>}
        <button
          type="button"
          className={styles.detalleLink}
          onClick={(e) => { e.stopPropagation(); onVerDetalle(caso.id) }}
        >
          Ver detalles <i className="ti ti-arrow-right" aria-hidden="true" />
        </button>
        </div>
      </div>
    </div>
  )
}
