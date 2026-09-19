// modules/casos/utils/etapas.js
//
// Helpers de presentación del seguimiento de casos. El catálogo de
// etapas (value/label/orden) viene del backend (GET /api/casos/etapas/);
// acá solo se decide cómo se ve cada una y cómo se formatean las fechas.

// Variante visual del badge según la etapa.
//  - muted:  todavía no empezó el proceso o ya terminó
//  - purple: proceso en curso
//  - ok:     hay resolución
const VARIANTE_POR_ETAPA = {
  registrado: 'muted',
  en_analisis: 'muted',
  investigacion_preliminar: 'purple',
  denuncia_demanda: 'purple',
  audiencias: 'purple',
  juicio: 'purple',
  sentencia: 'ok',
  apelacion: 'purple',
  cerrado: 'muted',
}

export function varianteEtapa(etapa) {
  return VARIANTE_POR_ETAPA[etapa] ?? 'muted'
}

export function formatFechaHora(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('es-BO', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Convierte el error de DRF ({ etapa: ['...'], nota: ['...'] } o
// { detail: '...' }) en un único mensaje legible.
export function mensajeErrorApi(error, fallback) {
  const data = error?.response?.data
  if (!data) return fallback
  if (typeof data === 'string') return fallback
  if (data.detail) return String(data.detail)
  const primero = Object.values(data).flat()[0]
  return typeof primero === 'string' ? primero : fallback
}
