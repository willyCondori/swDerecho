import { describe, expect, it } from 'vitest'
import { getEstadoBadge, getBorderClass } from './dashboardUtils'
describe('Estado real del análisis en el dashboard', () => {
  it.each([
    ['pendiente', 'Pendiente'], ['procesando', 'Analizando'],
    ['completado', 'Completo'], ['error', 'Con error'],
  ])('respeta %s aunque exista un resultado anterior', (estado_analisis, label) => {
    expect(getEstadoBadge({ estado_analisis, tiene_resultado: true }).label).toBe(label)
  })
  it('subir un PDF no implica haber iniciado un análisis', () => {
    expect(getEstadoBadge({ tiene_documento: true }).label).toBe('Pendiente')
  })
  it('mantiene compatibilidad con resultados previos y distingue colores por estado', () => {
    expect(getEstadoBadge({ tiene_resultado: true }).label).toBe('Completo')
    expect(getBorderClass({ estado_analisis: 'procesando' })).not.toBe(getBorderClass({ estado_analisis: 'completado' }))
  })
})
