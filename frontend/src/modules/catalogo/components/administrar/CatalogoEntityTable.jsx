import DataTable from '../../../../components/ui/DataTable'
import styles from '../../pages/AdministrarCatalogoPage.module.css'

export default function CatalogoEntityTable({ rows, loading, error, onRetry,
  onEditar, onEliminar, onRecuperar, recoverLabel, empty }) {
  const columns = [
    {
      key: 'nombre',
      header: 'Nombre',
      skeletonWidth: 200,
      render: (item) => <span className={styles.itemNombre}>{item.nombre}</span>,
    },
    {
      key: 'descripcion',
      header: 'Descripción',
      skeletonWidth: 320,
      render: (item) => (
        <span className={styles.itemDescripcion}>{item.descripcion || 'Sin descripción'}</span>
      ),
    },
    {
      key: 'estado',
      header: 'Estado',
      skeletonWidth: 70,
      render: (item) => (
        <span className={`${styles.badge} ${item.estado ? styles.activo : styles.inactivo}`}>
          {item.estado ? 'Activa' : 'Eliminada'}
        </span>
      ),
    },
    {
      key: 'acciones',
      ariaLabel: 'Acciones',
      actions: true,
      render: (item) => (
        item.estado ? (
          <>
            <button type="button" className={styles.iconBtn} title="Editar" onClick={() => onEditar(item)}>
              <i className="ti ti-pencil" aria-hidden="true" />
            </button>
            <button type="button" className={styles.iconBtn} title="Eliminar" onClick={() => onEliminar(item)}>
              <i className="ti ti-trash" aria-hidden="true" />
            </button>
          </>
        ) : (
          <button type="button" className={styles.iconBtn} title={recoverLabel} onClick={() => onRecuperar(item)}>
            <i className="ti ti-rotate-clockwise" aria-hidden="true" />
          </button>
        )
      ),
    },
  ]

  return <DataTable columns={columns} rows={rows} loading={loading} error={error}
    onRetry={onRetry} skeletonRows={4} empty={empty} />
}
