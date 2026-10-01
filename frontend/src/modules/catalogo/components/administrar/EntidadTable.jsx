// modules/catalogo/components/administrar/EntidadTable.jsx
import DataTable from '../../../../components/ui/DataTable'
import styles from '../../pages/AdministrarCatalogoPage.module.css'

export default function EntidadTable({
  entidades,
  loading,
  error,
  busqueda,
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
      render: (entidad) => <span className={styles.itemNombre}>{entidad.nombre}</span>,
    },
    {
      key: 'descripcion',
      header: 'Descripción',
      skeletonWidth: 320,
      render: (entidad) => (
        <span className={styles.itemDescripcion}>{entidad.descripcion || 'Sin descripción'}</span>
      ),
    },
    {
      key: 'estado',
      header: 'Estado',
      skeletonWidth: 70,
      render: (entidad) => (
        <span className={`${styles.badge} ${entidad.estado ? styles.activo : styles.inactivo}`}>
          {entidad.estado ? 'Activa' : 'Eliminada'}
        </span>
      ),
    },
    {
      key: 'acciones',
      ariaLabel: 'Acciones',
      actions: true,
      render: (entidad) => (
        entidad.estado ? (
          <>
            <button className={styles.iconBtn} title="Editar" onClick={() => onEditar(entidad)}>
              <i className="ti ti-pencil" aria-hidden="true" />
            </button>
            <button className={styles.iconBtn} title="Eliminar" onClick={() => onEliminar(entidad)}>
              <i className="ti ti-trash" aria-hidden="true" />
            </button>
          </>
        ) : (
          <button className={styles.iconBtn} title="Recuperar entidad" onClick={() => onRecuperar(entidad)}>
            <i className="ti ti-rotate-clockwise" aria-hidden="true" />
          </button>
        )
      ),
    },
  ]

  const empty = busqueda?.trim()
    ? { icon: 'ti-search', text: `No se encontraron entidades para “${busqueda.trim()}”.` }
    : {
        icon: 'ti-users',
        text: 'Todavía no hay entidades jurídicas registradas.',
        action: (
          <button className={styles.btnPrimary} onClick={onCrearPrimero}>
            <i className="ti ti-plus" aria-hidden="true" /> Nueva entidad
          </button>
        ),
      }

  return (
    <DataTable
      columns={columns}
      rows={entidades}
      loading={loading}
      error={error}
      onRetry={onRetry}
      skeletonRows={4}
      empty={empty}
    />
  )
}
