// modules/catalogo/components/administrar/JerarquiaTable.jsx
import DataTable from '../../../../components/ui/DataTable'
import styles from '../../pages/AdministrarCatalogoPage.module.css'

export default function JerarquiaTable({
  jerarquias,
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
      key: 'nivel',
      header: 'Nivel',
      skeletonWidth: 50,
      render: (j) => <span className={styles.badge}>{j.nivel}</span>,
    },
    {
      key: 'nombre',
      header: 'Nombre',
      skeletonWidth: 220,
      render: (j) => <span className={styles.itemNombre}>{j.nombre}</span>,
    },
    {
      key: 'estado',
      header: 'Estado',
      skeletonWidth: 70,
      render: (j) => (
        <span className={`${styles.badge} ${j.estado ? styles.activo : styles.inactivo}`}>
          {j.estado ? 'Activa' : 'Eliminada'}
        </span>
      ),
    },
    {
      key: 'acciones',
      ariaLabel: 'Acciones',
      actions: true,
      render: (j) => (
        j.estado ? (
          <>
            <button className={styles.iconBtn} title="Editar" onClick={() => onEditar(j)}>
              <i className="ti ti-pencil" aria-hidden="true" />
            </button>
            <button className={styles.iconBtn} title="Eliminar" onClick={() => onEliminar(j)}>
              <i className="ti ti-trash" aria-hidden="true" />
            </button>
          </>
        ) : (
          <button className={styles.iconBtn} title="Recuperar jerarquía" onClick={() => onRecuperar(j)}>
            <i className="ti ti-rotate-clockwise" aria-hidden="true" />
          </button>
        )
      ),
    },
  ]

  return (
    <DataTable
      columns={columns}
      rows={jerarquias}
      loading={loading}
      error={error}
      onRetry={onRetry}
      skeletonRows={4}
      empty={{
        icon: 'ti-stack-2',
        text: 'Todavía no hay jerarquías normativas registradas.',
        action: (
          <button className={styles.btnPrimary} onClick={onCrearPrimero}>
            <i className="ti ti-plus" aria-hidden="true" /> Nueva jerarquía
          </button>
        ),
      }}
    />
  )
}
