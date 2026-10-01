// modules/usuarios/components/RolTable.jsx
import DataTable from '../../../components/ui/DataTable'
import styles from '../pages/RolesPage.module.css'

const ROLES_SISTEMA = ['administrador']

export default function RolTable({
  roles,
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
      skeletonWidth: 140,
      render: (rol) => {
        const esRolSistema = ROLES_SISTEMA.includes(rol.nombre?.trim().toLowerCase())
        return (
          <div className={styles.rolNombre}>
            {rol.nombre}
            {esRolSistema && (
              <span className={styles.badgePurple} title="Rol del sistema, no se puede desactivar">
                <i className="ti ti-lock" aria-hidden="true" /> sistema
              </span>
            )}
          </div>
        )
      },
    },
    {
      key: 'descripcion',
      header: 'Descripción',
      skeletonWidth: 260,
      render: (rol) => (
        <span className={styles.rolDescripcion}>{rol.descripcion || 'Sin descripción'}</span>
      ),
    },
    {
      key: 'estado',
      header: 'Estado',
      skeletonWidth: 70,
      render: (rol) => (
        <span className={`${styles.badge} ${rol.estado ? styles.activo : styles.inactivo}`}>
          {rol.estado ? 'Activo' : 'Eliminado'}
        </span>
      ),
    },
    {
      key: 'acciones',
      ariaLabel: 'Acciones',
      actions: true,
      render: (rol) => {
        if (!rol.estado) {
          return (
            <button className={styles.iconBtn} title="Recuperar rol" onClick={() => onRecuperar(rol)}>
              <i className="ti ti-rotate-clockwise" aria-hidden="true" />
            </button>
          )
        }
        const esRolSistema = ROLES_SISTEMA.includes(rol.nombre?.trim().toLowerCase())
        return (
          <>
            <button className={styles.iconBtn} title="Editar" onClick={() => onEditar(rol)}>
              <i className="ti ti-pencil" aria-hidden="true" />
            </button>
            <button
              className={styles.iconBtn}
              title={esRolSistema ? 'El rol Administrador no puede desactivarse' : 'Eliminar'}
              disabled={esRolSistema}
              onClick={() => onEliminar(rol)}
            >
              <i className="ti ti-trash" aria-hidden="true" />
            </button>
          </>
        )
      },
    },
  ]

  return (
    <DataTable
      columns={columns}
      rows={roles}
      loading={loading}
      error={error}
      onRetry={onRetry}
      skeletonRows={4}
      empty={{
        icon: 'ti-shield-lock',
        text: 'No se encontraron roles.',
        action: (
          <button className={styles.btnPrimary} onClick={onCrearPrimero}>
            <i className="ti ti-shield-plus" aria-hidden="true" /> Nuevo rol
          </button>
        ),
      }}
    />
  )
}
