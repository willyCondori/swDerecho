// components/ui/DataTable.jsx
import styles from './DataTable.module.css'

/**
 * Tabla de datos reutilizable. Cada columna se describe en un arreglo, así que
 * los encabezados, el esqueleto de carga y las celdas de cada fila salen de la
 * MISMA lista y nunca pueden quedar con distinta cantidad de columnas.
 *
 * Ya incluye, para que ninguna pantalla tenga que repetirlos:
 *   - contenedor con scroll horizontal (en el celular la tabla se desliza en
 *     vez de quedar recortada por la card),
 *   - esqueleto de carga,
 *   - estado de error (con botón Reintentar) y estado vacío.
 *
 * Props
 *   columns     Arreglo de columnas (ver abajo). Obligatorio.
 *   rows        Filas a mostrar.
 *   rowKey      (fila) => clave única. Por defecto fila.id.
 *   loading     true → muestra el esqueleto (tiene prioridad sobre error/vacío).
 *   error       Mensaje de error (string). Si hay error y no se está cargando,
 *               se muestra el estado de error en lugar de la tabla.
 *   onRetry     Si se pasa, el estado de error muestra el botón "Reintentar".
 *   empty       { icon, text, action } para cuando no hay filas. icon es una
 *               clase de Tabler ('ti-users'); action es un nodo (p. ej. un botón).
 *   onRowClick  (fila) => void. Hace clicable la fila entera.
 *   skeletonRows  Filas del esqueleto (por defecto 5).
 *   ariaLabel   Nombre accesible de la tabla.
 *   minWidth    Ancho mínimo en px antes de que aparezca el scroll (por defecto 600).
 *
 * Columna
 *   key            Identificador único de la columna. Obligatorio.
 *   header         Texto (o nodo) del encabezado.
 *   render         (fila, indice) => nodo. Por defecto muestra fila[key].
 *   actions        true → columna de botones: se alinea a la derecha, agrupa los
 *                  botones y evita que un clic en ellos dispare onRowClick.
 *   ariaLabel      Nombre accesible para columnas sin texto de encabezado.
 *   align          'right' para alinear a la derecha.
 *   className      Clase extra para las celdas <td> de la columna.
 *   skeletonWidth  Ancho (px) de la barra del esqueleto.
 */

const ANCHO_ESQUELETO = 120
const ANCHO_ESQUELETO_ACCIONES = 60
const SIN_DATOS = { icon: 'ti-inbox', text: 'No hay datos para mostrar.' }

function EstadoTabla({ icon, text, action }) {
  return (
    <div className={styles.emptyState}>
      <i className={`ti ${icon} ${styles.emptyIcon}`} aria-hidden="true" />
      <p className={styles.emptyText}>{text}</p>
      {action}
    </div>
  )
}

function alineadoADerecha(columna) {
  return columna.actions || columna.align === 'right'
}

function clasesCelda(columna) {
  const clases = [columna.className]
  if (columna.align === 'right') clases.push(styles.alignRight)
  return clases.filter(Boolean).join(' ') || undefined
}

function Esqueleto({ columns, filas }) {
  return Array.from({ length: filas }).map((_, i) => (
    <tr key={i}>
      {columns.map((col) => (
        <td key={col.key}>
          <div
            className={styles.skeleton}
            style={{
              width: col.skeletonWidth ?? (col.actions ? ANCHO_ESQUELETO_ACCIONES : ANCHO_ESQUELETO),
              marginLeft: alineadoADerecha(col) ? 'auto' : undefined,
            }}
          />
        </td>
      ))}
    </tr>
  ))
}

export default function DataTable({
  columns,
  rows,
  rowKey = (fila) => fila.id,
  loading = false,
  error = null,
  onRetry,
  empty = SIN_DATOS,
  onRowClick,
  skeletonRows = 5,
  ariaLabel,
  minWidth,
}) {
  const filas = rows ?? []

  if (!loading && error) {
    return (
      <EstadoTabla
        icon="ti-wifi-off"
        text={typeof error === 'string' ? error : 'No se pudieron cargar los datos.'}
        action={onRetry && (
          <button type="button" className={styles.btnSecondary} onClick={onRetry}>
            Reintentar
          </button>
        )}
      />
    )
  }

  if (!loading && filas.length === 0) {
    return <EstadoTabla {...empty} />
  }

  return (
    <div className={styles.tableScroll}>
      <table
        className={styles.table}
        aria-label={ariaLabel}
        aria-busy={loading || undefined}
        style={minWidth ? { minWidth } : undefined}
      >
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                aria-label={col.ariaLabel}
                className={alineadoADerecha(col) ? styles.alignRight : undefined}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <Esqueleto columns={columns} filas={skeletonRows} />
          ) : (
            filas.map((fila, indice) => (
              <tr
                key={rowKey(fila)}
                onClick={onRowClick ? () => onRowClick(fila) : undefined}
              >
                {columns.map((col) => {
                  const contenido = col.render ? col.render(fila, indice) : fila[col.key]
                  return (
                    <td key={col.key} className={clasesCelda(col)}>
                      {col.actions ? (
                        <div className={styles.actionsCell} onClick={(e) => e.stopPropagation()}>
                          {contenido}
                        </div>
                      ) : contenido}
                    </td>
                  )
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
