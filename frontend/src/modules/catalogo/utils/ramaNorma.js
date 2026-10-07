const clave = (valor) => String(valor || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim()

export function ramaDeNorma(norma, ramas) {
  if (!norma) return ''
  const asociadas = [...new Set((norma.ramas || []).map((r) => String(r.id)))]
  if (asociadas.length) return asociadas.length === 1 && ramas.some((r) => String(r.id) === asociadas[0]) ? asociadas[0] : ''
  // Compatibilidad con listados antiguos y códigos todavía sin artículos cargados.
  const penal = /^(?:codigo penal|codigo de procedimiento penal)(?:\s|$)/.test(clave(norma.nombre)) || ['cp', 'cpp'].includes(clave(norma.sigla))
  if (!penal) return ''
  const candidatas = ramas.filter((r) => ['penal', 'derecho penal'].includes(clave(r.nombre)))
  return candidatas.length === 1 ? String(candidatas[0].id) : ''
}
