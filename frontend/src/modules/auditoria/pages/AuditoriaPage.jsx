// modules/auditoria/pages/AuditoriaPage.jsx
import useAuditoria from '../hooks/useAuditoria'
import DataTable from '../../../components/ui/DataTable'
import Pagination from '../../../components/ui/Pagination'
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

const COLUMNAS = [
  {
    key: 'usuario',
    header: 'Usuario',
    skeletonWidth: 120,
    className: styles.usuarioCell,
    render: (r) => r.usuario?.usuario || '—',
  },
  {
    key: 'tabla',
    header: 'Tabla',
    skeletonWidth: 100,
    className: styles.tablaCell,
    render: (r) => r.tabla,
  },
  {
    key: 'accion',
    header: 'Acción',
    skeletonWidth: 80,
    render: (r) => (
      <span className={`${styles.badge} ${claseAccion(r.accion)}`}>
        {r.accion_label || r.accion}
      </span>
    ),
  },
  {
    key: 'registro',
    header: 'Registro',
    skeletonWidth: 60,
    render: (r) => r.registro_id ?? '—',
  },
  {
    key: 'fecha',
    header: 'Fecha',
    skeletonWidth: 130,
    className: styles.fechaCell,
    render: (r) => formatFecha(r.created_at),
  },
]

export default function AuditoriaPage() {
  const {
    registros, loading, error, count,
    page, setPage, totalPages, pageSize,
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
            <label className={styles.label} htmlFor="filtroUsuario">Usuario</label>
            <input
              id="filtroUsuario"
              className={styles.input}
              placeholder="ej: jperez"
              value={filtros.usuario}
              onChange={(e) => setFiltro('usuario', e.target.value)}
            />
          </div>

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
        <DataTable
          columns={COLUMNAS}
          rows={registros}
          loading={loading}
          error={error}
          onRetry={reload}
          skeletonRows={6}
          empty={{
            icon: 'ti-shield-check',
            text: 'No hay registros de auditoría con estos filtros.',
          }}
        />
        {!loading && !error && (
          <Pagination
            page={page}
            totalPages={totalPages}
            count={count}
            pageSize={pageSize}
            onPageChange={setPage}
            itemLabel="registros"
          />
        )}
      </div>
    </div>
  )
}
