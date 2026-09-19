// modules/clientes/pages/PapeleraClientesPage.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import usePapeleraClientes from '../hooks/usePapeleraClientes'
import DataTable from '../../../components/ui/DataTable'
import { formatFechaHora } from '../../casos/utils/etapas'
import styles from './PapeleraClientesPage.module.css'

export function textoEliminacion(cliente) {
  if (!cliente.eliminado_at) return 'Eliminado antes de que existiera la papelera (fecha desconocida)'
  const cuando = formatFechaHora(cliente.eliminado_at)
  return cliente.eliminado_por_nombre
    ? `${cuando} por ${cliente.eliminado_por_nombre}`
    : cuando
}

export function textoCasos(n) {
  return `${n} ${n === 1 ? 'caso' : 'casos'}`
}

export default function PapeleraClientesPage() {
  const navigate = useNavigate()
  const [errorRestaurar, setErrorRestaurar] = useState('')
  const [restaurado, setRestaurado] = useState('')
  const {
    clientes, loading, error, page, setPage, totalPages, count,
    search, setSearch, restaurar, restaurandoId, reload,
  } = usePapeleraClientes()

  const handleRestaurar = async (cliente) => {
    const n = cliente.casos_para_restaurar ?? 0
    const aviso = n > 0
      ? ` También volverán ${n === 1 ? 'su caso eliminado con él' : `sus ${n} casos eliminados con él`}.`
      : ''
    if (!window.confirm(`¿Restaurar a ${cliente.nombre_completo}?${aviso}`)) return

    setErrorRestaurar('')
    setRestaurado('')
    const res = await restaurar(cliente.id)
    if (res.ok) {
      setRestaurado(
        res.casosRestaurados > 0
          ? `${cliente.nombre_completo} fue restaurado, junto con ${textoCasos(res.casosRestaurados)}.`
          : `${cliente.nombre_completo} fue restaurado.`
      )
    } else {
      setErrorRestaurar(res.error)
    }
  }

  const columns = [
    {
      key: 'cliente',
      header: 'Cliente',
      skeletonWidth: 180,
      className: styles.clienteNombre,
      render: (c) => c.nombre_completo,
    },
    {
      key: 'telefono',
      header: 'Teléfono',
      skeletonWidth: 100,
      className: styles.meta,
      render: (c) => c.telefono || '—',
    },
    {
      key: 'eliminado',
      header: 'Eliminado',
      skeletonWidth: 200,
      className: styles.meta,
      render: (c) => textoEliminacion(c),
    },
    {
      key: 'casos',
      header: 'Casos que volverán',
      skeletonWidth: 80,
      render: (c) => (
        c.casos_para_restaurar > 0
          ? <span className={`${styles.badge} ${styles.conCasos}`}>{textoCasos(c.casos_para_restaurar)}</span>
          : <span className={styles.sinCasos}>—</span>
      ),
    },
    {
      key: 'acciones',
      ariaLabel: 'Acciones',
      actions: true,
      render: (c) => (
        <button
          type="button"
          className={styles.btnPrimary}
          onClick={() => handleRestaurar(c)}
          disabled={restaurandoId === c.id}
        >
          <i className="ti ti-restore" aria-hidden="true" />{' '}
          {restaurandoId === c.id ? 'Restaurando...' : 'Restaurar'}
        </button>
      ),
    },
  ]

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Papelera de clientes</h1>
          <p className={styles.subtitle}>
            Clientes eliminados. Al restaurar uno vuelven también los casos que se eliminaron junto con él.
          </p>
        </div>
        <div className={styles.headerActions}>
          <button className={styles.btnSecondary} onClick={() => navigate('/clientes')}>
            <i className="ti ti-arrow-left" aria-hidden="true" />
            Volver a clientes
          </button>
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
            {count} {count === 1 ? 'cliente eliminado' : 'clientes eliminados'}
          </span>
        )}
      </div>

      {errorRestaurar && <div className={styles.errorBanner}>{errorRestaurar}</div>}
      {restaurado && <div className={styles.resultCount} role="status">{restaurado}</div>}

      <div className={styles.card}>
        <DataTable
          columns={columns}
          rows={clientes}
          loading={loading}
          error={error}
          onRetry={reload}
          empty={{
            icon: 'ti-trash-off',
            text: search.trim().length >= 2
              ? 'No se encontraron clientes eliminados con esa búsqueda.'
              : 'La papelera está vacía.',
          }}
        />

        {!loading && !error && clientes.length > 0 && totalPages > 1 && (
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
