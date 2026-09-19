// modules/catalogo/components/administrar/RamaTable.jsx
import DataTable from '../../../../components/ui/DataTable'
import styles from '../../pages/AdministrarCatalogoPage.module.css'

export default function RamaTable({
  ramas,
  loading,
  error,
  onRetry,
  onEditar,
  onEliminar,
  onRecuperar,
  onCrearPrimero,
}) {
  const columns = [
    {
      key: 'nombre',
      header: 'Nombre',
      skeletonWidth: 200,
      render: (rama) => <span className={styles.itemNombre}>{rama.nombre}</span>,
    },
    {
      key: 'descripcion',
      header: 'Descripción',
      skeletonWidth: 320,
      render: (rama) => (
        <span className={styles.itemDescripcion}>{rama.descripcion || 'Sin descripción'}</span>
      ),
    },
    {
      key: 'estado',
      header: 'Estado',
      skeletonWidth: 70,
      render: (rama) => (
        <span className={`${styles.badge} ${rama.estado ? styles.activo : styles.inactivo}`}>
          {rama.estado ? 'Activa' : 'Eliminada'}
        </span>
      ),
    },
    {
      key: 'acciones',
      ariaLabel: 'Acciones',
      actions: true,
      render: (rama) => (
        rama.estado ? (
          <>
            <button className={styles.iconBtn} title="Editar" onClick={() => onEditar(rama)}>
              <i className="ti ti-pencil" aria-hidden="true" />
            </button>
            <button className={styles.iconBtn} title="Eliminar" onClick={() => onEliminar(rama)}>
              <i className="ti ti-trash" aria-hidden="true" />
            </button>
          </>
        ) : (
          <button className={styles.iconBtn} title="Recuperar rama" onClick={() => onRecuperar(rama)}>
            <i className="ti ti-rotate-clockwise" aria-hidden="true" />
          </button>
        )
      ),
    },
  ]

  return (
    <DataTable
      columns={columns}
      rows={ramas}
      loading={loading}
      error={error}
      onRetry={onRetry}
      skeletonRows={4}
      empty={{
        icon: 'ti-gavel',
        text: 'Todavía no hay ramas de derecho registradas.',
        action: (
          <button className={styles.btnPrimary} onClick={onCrearPrimero}>
            <i className="ti ti-plus" aria-hidden="true" /> Nueva rama
          </button>
        ),
      }}
    />
  )
}
