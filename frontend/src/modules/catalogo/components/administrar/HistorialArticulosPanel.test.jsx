import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import HistorialArticulosPanel from './HistorialArticulosPanel'
const mocks = vi.hoisted(() => ({ historial: vi.fn() }))
vi.mock('../../../../api/normativaApi', () => ({ default: { historial: mocks.historial } }))
vi.mock('../../../../api/catalogoApi', () => ({ default: { normas: vi.fn().mockResolvedValue({ data: [{ id: 5, nombre: 'Código Penal' }] }) } }))
afterEach(cleanup)
it('muestra el antes y después, fuente y alcance y permite filtrar por norma y operación', async () => {
  mocks.historial.mockResolvedValue({ data: { results: [{ id: 1, norma: 'Código Penal', numero_articulo: '323 BIS', operacion: 'deroga',
    norma_causante: 'LEY 1636', fecha_efecto: '2025-09-10', disposicion_fuente: 'disposición derogatoria única', aplicado: true,
    parte_afectada: { tipo: 'parcial', descripcion: 'Parágrafo III' }, texto_antes: 'I. Texto vigente. III. Texto derogado.', texto_despues: 'I. Texto vigente.',
    revisado_por: 'Administrador', cita: 'Se deroga el Parágrafo III.' }], next: null } })
  render(<HistorialArticulosPanel />)
  expect(await screen.findByText('Código Penal · Artículo 323 BIS')).toBeTruthy()
  expect(screen.getByText('Parte derogada retirada del texto activo.')).toBeTruthy()
  expect(screen.getByRole('region', { name: 'Texto antes del cambio' }).querySelector('pre').textContent).toBe('I. Texto vigente. III. Texto derogado.')
  expect(screen.getByRole('region', { name: 'Texto después del cambio' }).querySelector('pre').textContent).toBe('I. Texto vigente.')
  fireEvent.change(screen.getByLabelText('Norma'), { target: { value: '5' } })
  fireEvent.change(screen.getByLabelText('Tipo de cambio'), { target: { value: 'deroga' } })
  await waitFor(() => expect(mocks.historial).toHaveBeenLastCalledWith({ norma: '5', operacion: 'deroga', page: 1 }))
})
it('distingue una derogación programada sin decir que ya retiró el texto', async () => {
  mocks.historial.mockResolvedValue({ data: { results: [{ id: 2, norma: 'Ley anterior', numero_articulo: '1', operacion: 'abroga', aplicado: false,
    fecha_efecto: '2099-01-01', parte_afectada: {}, texto_antes: 'Texto original.', texto_despues: 'Texto original.' }] } })
  render(<HistorialArticulosPanel />)
  expect(await screen.findByText('Programado: todavía no aplicado al texto activo.')).toBeTruthy()
  expect(screen.getByText('Después previsto')).toBeTruthy()
})
