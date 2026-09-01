// modules/auditoria/pages/AuditoriaPage.jsx
import useAuditoria from '../hooks/useAuditoria'
import styles from './AuditoriaPage.module.css'

function claseAccion(accion) {
  switch (accion) {
    case 'CREATE': return styles.accionCreate
    case 'UPDATE': return styles.accionUpdate
    case 'DELETE': return styles.accionDelete
    case 'LOGIN':  return styles.accionLogin
    case 'LOGOUT': return styles.accionLogout
    default:       return styles.accionBadge
  }
}

function formatFecha(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('es-BO', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function SkeletonRows({ rows = 6 }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i}>
          <td><div className={styles.skeleton} style={{ width: 120 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 100 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 80 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 60 }} /></td>
          <td><div className={styles.skeleton} style={{ width: 130 }} /></td>
        </tr>
      ))}
    </>
  )
}

export default function AuditoriaPage() {
  const {
    registros, loading, error, count,
    filtros, setFiltro, limpiarFiltros,
    acciones, reload,
  } = useAuditoria()

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Auditoría</h1>
          <p className={styles.subtitle}>
            Historial de acciones CREATE / UPDATE / DELETE sobre roles, usuarios y otros módulos.
          </p>
        </div>
      </header>

      {/* ── Filtros ─────────────────────────────── */}
      <div className={styles.cardPadded}>
        <div className={styles.filtros}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="filtroTabla">Tabla</label>
            <input
              id="filtroTabla"
              className={styles.input}
              placeholder="ej: roles, usuarios"
              value={filtros.tabla}
              onChange={(e) => setFiltro('tabla', e.target.value)}
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="filtroAccion">Acción</label>
            <select
              id="filtroAccion"
              className={styles.select}
              value={filtros.accion}
              onChange={(e) => setFiltro('accion', e.target.value)}
            >
              <option value="">Todas</option>
              {acciones.map((a) => (
                <option key={a.value} value={a.value}>{a.label}</option>
              ))}
            </select>
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="filtroDesde">Desde</label>
            <input
              id="filtroDesde"
              type="date"
              className={styles.input}
              value={filtros.fecha_desde}
              onChange={(e) => setFiltro('fecha_desde', e.target.value)}
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="filtroHasta">Hasta</label>
            <input
              id="filtroHasta"
              type="date"
              className={styles.input}
              value={filtros.fecha_hasta}
              onChange={(e) => setFiltro('fecha_hasta', e.target.value)}
            />
          </div>

          <button className={styles.btnLimpiar} onClick={limpiarFiltros}>
            <i className="ti ti-filter-off" aria-hidden="true" />
            Limpiar
          </button>
        </div>
      </div>

      {!loading && !error && (
        <span className={styles.resultCount}>
          {count} {count === 1 ? 'registro' : 'registros'}
        </span>
      )}

      {/* ── Tabla ──────────────────────────────── */}
      <div className={styles.card}>
        {!loading && error && (
          <div className={styles.emptyState}>
            <i className={`ti ti-wifi-off ${styles.emptyIcon}`} aria-hidden="true" />
            <p className={styles.emptyText}>{error}</p>
            <button className={styles.btnSecondary} onClick={reload}>Reintentar</button>
          </div>
        )}

        {!loading && !error && registros.length === 0 && (
          <div className={styles.emptyState}>
            <i className={`ti ti-shield-check ${styles.emptyIcon}`} aria-hidden="true" />
            <p className={styles.emptyText}>No hay registros de auditoría con estos filtros.</p>
          </div>
        )}

        {(loading || (!error && registros.length > 0)) && (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Tabla</th>
                <th>Acción</th>
                <th>Registro</th>
                <th>Fecha</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <SkeletonRows />
              ) : (
                registros.map((r) => (
                  <tr key={r.id}>
                    <td className={styles.usuarioCell}>{r.usuario?.usuario || '—'}</td>
                    <td className={styles.tablaCell}>{r.tabla}</td>
                    <td>
                      <span className={`${styles.badge} ${claseAccion(r.accion)}`}>
                        {r.accion_label || r.accion}
                      </span>
                    </td>
                    <td>{r.registro_id ?? '—'}</td>
                    <td className={styles.fechaCell}>{formatFecha(r.created_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
