// modules/clientes/pages/ClientesPage.jsx
import { useNavigate } from 'react-router-dom'
import useClientes from '../hooks/useClientes'
import useAuthStore from '../../auth/store/authStore'
import DataTable from '../../../components/ui/DataTable'
import { eliminarClienteConCasos } from '../utils/eliminarCliente'
import styles from './ClientesPage.module.css'

function getNombreCompleto(cliente) {
  const nombres = cliente.nombres ?? ''
  const apellidos = cliente.apellidos ?? ''
  return `${nombres} ${apellidos}`.trim() || `Cliente #${cliente.id}`
}

export default function ClientesPage() {
  const navigate = useNavigate()
  const puedeEscribir = useAuthStore((s) => s.puedeEscribir())
  const {
    clientes, loading, error, search, setSearch, buscando,
    page, setPage, totalPages, count, reload, eliminarCliente,
  } = useClientes()

  const handleEliminar = (cliente) =>
    eliminarClienteConCasos({
      nombre: getNombreCompleto(cliente),
      eliminar: (opciones) => eliminarCliente(cliente.id, opciones),
    })

  const columns = [
    {
      key: 'nombre',
      header: 'Cliente',
      skeletonWidth: 180,
      className: styles.clienteNombre,
      render: (cliente) => getNombreCompleto(cliente),
    },
    {
      key: 'telefono',
      header: 'Teléfono',
      skeletonWidth: 140,
      className: styles.clienteMeta,
      render: (cliente) => cliente.telefono || '—',
    },
    ...(puedeEscribir ? [{
      key: 'acciones',
      ariaLabel: 'Acciones',
      actions: true,
      render: (cliente) => (
        <>
          <button
            className={styles.iconBtn}
            title="Editar"
            onClick={() => navigate(`/clientes/${cliente.id}/editar`)}
          >
            <i className="ti ti-pencil" aria-hidden="true" />
          </button>
          <button className={styles.iconBtn} title="Eliminar" onClick={() => handleEliminar(cliente)}>
            <i className="ti ti-trash" aria-hidden="true" />
          </button>
        </>
      ),
    }] : []),
  ]

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Clientes</h1>
          <p className={styles.subtitle}>Datos de contacto de tus clientes.</p>
        </div>
        <div className={styles.headerActions}>
          {puedeEscribir && (
            <button className={styles.btnSecondary} onClick={() => navigate('/clientes/papelera')}>
              <i className="ti ti-trash" aria-hidden="true" />
              Papelera
            </button>
          )}
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
        <DataTable
          columns={columns}
          rows={clientes}
          loading={loading}
          error={error}
          onRetry={reload}
          onRowClick={(cliente) => navigate(`/clientes/${cliente.id}`)}
          empty={{
            icon: 'ti-users',
            text: buscando ? 'Sin resultados para tu búsqueda.' : 'No hay clientes registrados aún.',
            action: !buscando && puedeEscribir && (
              <button className={styles.btnPrimary} onClick={() => navigate('/clientes/nuevo')}>
                <i className="ti ti-plus" aria-hidden="true" /> Crear primer cliente
              </button>
            ),
          }}
        />

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