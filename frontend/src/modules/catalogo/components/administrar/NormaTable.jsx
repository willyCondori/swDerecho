// modules/catalogo/components/administrar/NormaTable.jsx
import DataTable from '../../../../components/ui/DataTable'
import styles from '../../pages/AdministrarCatalogoPage.module.css'

export default function NormaTable({
  normas,
  loading,
  error,
  busqueda,
  mostrandoEliminadas,
  onRetry,
  onEliminar,
  onRecuperar,
  onVerDocumentos,
}) {
  const columns = [
    {
      key: 'nombre',
      header: 'Nombre',
      skeletonWidth: 260,
      render: (norma) => <span className={styles.itemNombre}>{norma.nombre}</span>,
    },
    {
      key: 'sigla',
      header: 'Sigla',
      skeletonWidth: 60,
      render: (norma) => <span className={styles.itemDescripcion}>{norma.sigla || '—'}</span>,
    },
    {
      key: 'jerarquia',
      header: 'Jerarquía',
      skeletonWidth: 140,
      render: (norma) => (
        <span className={styles.itemDescripcion}>{norma.jerarquia?.nombre || 'Sin jerarquía'}</span>
      ),
    },
    {
      key: 'estado',
      header: 'Estado',
      skeletonWidth: 70,
      render: (norma) => (
        <span className={`${styles.badge} ${norma.estado ? styles.activo : styles.inactivo}`}>
          {norma.estado ? 'Activa' : 'Eliminada'}
        </span>
      ),
    },
    {
      key: 'acciones',
      ariaLabel: 'Acciones',
      actions: true,
      skeletonWidth: 40,
      render: (norma) => (
        <>
          <button className={styles.iconBtn} title="Ver documentos" onClick={() => onVerDocumentos(norma)}>
            <i className="ti ti-folder" aria-hidden="true" />
          </button>
          {norma.estado ? (
            <button className={styles.iconBtn} title="Eliminar" onClick={() => onEliminar(norma)}>
              <i className="ti ti-trash" aria-hidden="true" />
            </button>
          ) : (
            <button className={styles.iconBtn} title="Recuperar norma" onClick={() => onRecuperar(norma)}>
              <i className="ti ti-rotate-clockwise" aria-hidden="true" />
            </button>
          )}
        </>
      ),
    },
  ]

  const empty = busqueda?.trim()
    ? { icon: 'ti-search', text: `No se encontraron normas para “${busqueda.trim()}”.` }
    : {
        icon: 'ti-books',
        text: mostrandoEliminadas
          ? 'No hay normas eliminadas.'
          : 'Todavía no hay normas registradas. Se crean al cargar un PDF de artículos.',
      }

  return (
    <DataTable
      columns={columns}
      rows={normas}
      loading={loading}
      error={error}
      onRetry={onRetry}
      skeletonRows={4}
      empty={empty}
    />
  )
}
