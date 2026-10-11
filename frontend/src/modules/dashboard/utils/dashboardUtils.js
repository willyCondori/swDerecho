// modules/dashboard/utils/dashboardUtils.js
import styles from '../pages/DashboardPage.module.css'

export function getEstadoBadge(caso) {
  if (caso.estado_analisis === 'error') return { label: 'Con error', cls: styles.error }
  if (caso.estado_analisis === 'procesando') return { label: 'Analizando', cls: styles.analizando }
  if (caso.estado_analisis === 'pendiente') return { label: 'Pendiente', cls: styles.pendiente }
  if (caso.estado_analisis === 'completado') return { label: 'Completo', cls: styles.completo }
  if (caso.tiene_resultado) return { label: 'Completo', cls: styles.completo }
  return { label: 'Pendiente', cls: styles.pendiente }
}

export function getBorderClass(caso) {
  const estado = getEstadoBadge(caso).label
  if (estado === 'Completo') return styles.borderGreen
  if (estado === 'Analizando') return styles.borderPurple
  return styles.borderAmber
}

export function formatFecha(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const diff = Math.floor((Date.now() - d) / 1000)
  if (diff < 3600) return `hace ${Math.floor(diff / 60)}m`
  if (diff < 86400) return `hace ${Math.floor(diff / 3600)}h`
  return d.toLocaleDateString('es-BO', { day: 'numeric', month: 'short' })
}

export function getGreeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Buenos días'
  if (h < 18) return 'Buenas tardes'
  return 'Buenas noches'
}

export function computeCasoStats(casos) {
  const total = casos.length
  const completos = casos.filter((c) => c.tiene_resultado).length
  const conPdf = casos.filter((c) => c.tiene_documento).length
  const pendientes = total - completos
  return { total, completos, conPdf, pendientes }
}
