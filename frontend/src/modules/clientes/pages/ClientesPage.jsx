// modules/clientes/pages/ClientesPage.jsx
import { useNavigate } from 'react-router-dom'
import useClientes from '../hooks/useClientes'
import useAuthStore from '../../auth/store/authStore'
import styles from './ClientesPage.module.css'

function getNombreCompleto(cliente) {
  const nombres = cliente.nombres ?? ''
  const apellidos = cliente.apellidos ?? ''
  return `${nombres} ${apellidos}`.trim() || `Cliente #${cliente.id}`
}

function SkeletonRows() {
  return Array.from({ length: 5 }).map((_, i) => (
    <tr key={i}>
      <td><div className={styles.skeleton} style={{ width: 180 }} /></td>
      <td><div className={styles.skeleton} style={{ width: 140 }} /></td>
      <td><div className={styles.skeleton} style={{ width: 100 }} /></td>
      <td><div className={styles.skeleton} style={{ width: 60, marginLeft: 'auto' }} /></td>
    </tr>
  ))
}

export default function ClientesPage() {
  const navigate = useNavigate()
  const puedeEscribir = useAuthStore((s) => s.puedeEscribir())
  const {
    clientes, loading, error, search, setSearch, buscando,
    page, setPage, totalPages, count, reload, eliminarCliente,
  } = useClientes()

  const handleEliminar = async (cliente) => {
    if (!window.confirm(`¿Eliminar a ${getNombreCompleto(cliente)}?`)) return
    try {
      await eliminarCliente(cliente.id)
    } catch (e) {
      window.alert(e?.response?.data?.detail || 'No se pudo eliminar el cliente.')
    }
  }

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Clientes</h1>
          <p className={styles.subtitle}>Datos de contacto de tus clientes.</p>
        </div>
        <div className={styles.headerActions}>
          {puedeEscribir && (
            <button className={styles.btnPrimary} onClick={() => navigate('/clientes/nuevo')}>
              <i className="ti ti-user-plus" aria-hidden="true" />
              Nuevo cliente
            </button>
          )}
        </div>
      </header>

      <div className={styles.toolbar}>
        <div className={styles.searchBox}>
          <i className={`ti ti-search ${styles.searchIcon}`} aria-hidden="true" />
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Buscar por nombre o apellido..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        {!loading && !error && (
          <span className={styles.resultCount}>
            {count} {count === 1 ? 'cliente' : 'clientes'}
          </span>
        )}
      </div>

      <div className={styles.card}>
        {!loading && error ? (
          <div className={styles.emptyState}>
            <i className={`ti ti-wifi-off ${styles.emptyIcon}`} aria-hidden="true" />
            <p className={styles.emptyText}>{error}</p>
            <button className={styles.btnSecondary} onClick={reload}>Reintentar</button>
          </div>
        ) : !loading && clientes.length === 0 ? (
          <div className={styles.emptyState}>
            <i className={`ti ti-users ${styles.emptyIcon}`} aria-hidden="true" />
            <p className={styles.emptyText}>
              {buscando ? 'Sin resultados para tu búsqueda.' : 'No hay clientes registrados aún.'}
            </p>
            {!buscando && puedeEscribir && (
              <button className={styles.btnPrimary} onClick={() => navigate('/clientes/nuevo')}>
                <i className="ti ti-plus" aria-hidden="true" /> Crear primer cliente
              </button>
            )}
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Teléfono</th>
                {puedeEscribir && <th aria-label="Acciones" />}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <SkeletonRows />
              ) : (
                clientes.map((cliente) => (
                  <tr key={cliente.id} onClick={() => navigate(`/clientes/${cliente.id}`)}>
                    <td className={styles.clienteNombre}>{getNombreCompleto(cliente)}</td>
                    <td className={styles.clienteMeta}>{cliente.telefono || '—'}</td>
                    {puedeEscribir && (
                      <td>
                        <div className={styles.actionsCell} onClick={(e) => e.stopPropagation()}>
                          <button className={styles.iconBtn} title="Eliminar" onClick={() => handleEliminar(cliente)}>
                            <i className="ti ti-trash" aria-hidden="true" />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}

        {!loading && !error && !buscando && clientes.length > 0 && totalPages > 1 && (
          <div className={styles.pagination}>
            <span className={styles.pageInfo}>Página {page} de {totalPages}</span>
            <div className={styles.pageControls}>
              <button className={styles.btnSecondary} disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
                <i className="ti ti-chevron-left" aria-hidden="true" />
              </button>
              <button className={styles.btnSecondary} disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>
                <i className="ti ti-chevron-right" aria-hidden="true" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}