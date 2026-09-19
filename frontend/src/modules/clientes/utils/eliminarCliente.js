// modules/clientes/utils/eliminarCliente.js

export const textoCasosActivos = (n) => `${n} ${n === 1 ? 'caso activo' : 'casos activos'}`

/**
 * Flujo para eliminar un cliente (lo envía a la papelera):
 *   1. Pide confirmación.
 *   2. Si el cliente tiene casos activos el backend responde 400 con
 *      code 'cliente_con_casos_activos': se pregunta si también se eliminan
 *      sus casos (irán a la papelera y volverán al restaurar al cliente).
 *   3. Cualquier otro error se muestra tal cual.
 *
 * `eliminar(opciones)` hace la llamada a la API (opciones: { eliminarCasos }).
 * `confirmar` y `avisar` se inyectan (por defecto window.confirm / window.alert)
 * para poder probar el flujo.
 *
 * Devuelve { eliminado: boolean, casos: número de casos eliminados con él }.
 */
export async function eliminarClienteConCasos({
  nombre,
  eliminar,
  confirmar = (texto) => window.confirm(texto),
  avisar = (texto) => window.alert(texto),
}) {
  if (!confirmar(`¿Eliminar a ${nombre}? Podrás restaurarlo desde Clientes → Papelera.`)) {
    return { eliminado: false, casos: 0 }
  }

  try {
    await eliminar()
    return { eliminado: true, casos: 0 }
  } catch (e) {
    const data = e?.response?.data
    if (data?.code !== 'cliente_con_casos_activos') {
      avisar(data?.detail || 'No se pudo eliminar el cliente.')
      return { eliminado: false, casos: 0 }
    }

    const n = data.casos_activos ?? 0
    const deseaEliminarCasos = confirmar(
      `${nombre} tiene ${textoCasosActivos(n)}. ¿Eliminar también ${n === 1 ? 'ese caso' : 'esos casos'}? ` +
      'Se enviarán a la papelera y volverán cuando restaures al cliente.'
    )
    if (!deseaEliminarCasos) return { eliminado: false, casos: 0 }

    try {
      await eliminar({ eliminarCasos: true })
      return { eliminado: true, casos: n }
    } catch (e2) {
      avisar(e2?.response?.data?.detail || 'No se pudo eliminar el cliente.')
      return { eliminado: false, casos: 0 }
    }
  }
}
