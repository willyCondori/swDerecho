// Localiza la cita recuperada, conservando el texto original de la resolución.
// Solo tolera diferencias de espacios y saltos de línea; no inventa coincidencias.
export default function localizarFragmento(texto, fragmento) {
  if (!texto || !fragmento?.trim()) return null
  const literal = fragmento.trim()
  const inicio = texto.indexOf(literal)
  if (inicio !== -1) return { inicio, fin: inicio + literal.length }
  const patron = literal.split(/\s+/).map(p => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('\\s+')
  const coincidencia = new RegExp(patron, 'u').exec(texto)
  return coincidencia ? { inicio: coincidencia.index, fin: coincidencia.index + coincidencia[0].length } : null
}
