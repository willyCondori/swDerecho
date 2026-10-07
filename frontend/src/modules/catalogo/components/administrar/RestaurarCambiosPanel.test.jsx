import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import RestaurarCambiosPanel from './RestaurarCambiosPanel'
const mocks = vi.hoisted(() => ({ grupos: vi.fn(), preparar: vi.fn(), restaurar: vi.fn() }))
vi.mock('../../../../api/normativaApi', () => ({ default: { gruposAvisos: mocks.grupos, prepararRestauracion: mocks.preparar, restaurarCambio: mocks.restaurar } }))
vi.mock('../../../../api/catalogoApi', () => ({ default: { normas: vi.fn().mockResolvedValue({ data: [] }) } }))
const cambio = { id: 2, operacion: 'deroga', estado_revision: 'confirmado', referencia: { norma: 'Código Penal', unidad: '323 BIS', alcance: 'Parágrafo III' } }
beforeEach(() => {
  vi.clearAllMocks()
  mocks.grupos.mockResolvedValue({ data: { results: [{ id: 1, norma_causante: 'LEY 1636', disposicion_fuente: 'disposición derogatoria única', cita: 'Se deroga el parágrafo III.', afectaciones: [cambio] }] } })
  mocks.preparar.mockResolvedValue({ data: { restaurable: true, historial: [{ id: 1, numero_articulo: '323 BIS', texto_antes: 'Texto anterior.', texto_despues: 'Texto sin el parágrafo.' }] } })
  mocks.restaurar.mockResolvedValue({ data: {} })
})
afterEach(cleanup)
it('exige revisar la vista previa antes de confirmar la restauración', async () => {
  render(<RestaurarCambiosPanel />)
  fireEvent.click(await screen.findByRole('button', { name: 'Revisar restauración' }))
  const confirmar = await screen.findByRole('button', { name: 'Confirmar restauración' })
  expect(mocks.restaurar).not.toHaveBeenCalled()
  expect(screen.getByRole('region', { name: 'Texto anterior a recuperar' }).querySelector('pre').textContent).toBe('Texto anterior.')
  expect(screen.getByRole('region', { name: 'Texto después del cambio original' }).querySelector('pre').textContent).toBe('Texto sin el parágrafo.')
  fireEvent.click(confirmar)
  await waitFor(() => expect(mocks.restaurar).toHaveBeenCalledWith(2))
  expect(await screen.findByText(/Restauración registrada. Puedes/)).toBeTruthy()
})
it('bloquea la restauración si existen cambios posteriores', async () => {
  mocks.preparar.mockResolvedValue({ data: { restaurable: false, detalle: 'El artículo cambió después de la derogación.', historial: [] } })
  render(<RestaurarCambiosPanel />)
  fireEvent.click(await screen.findByRole('button', { name: 'Revisar restauración' }))
  expect((await screen.findByRole('button', { name: 'Confirmar restauración' })).disabled).toBe(true)
  expect(screen.getByRole('alert').textContent).toContain('cambió después')
  expect(mocks.restaurar).not.toHaveBeenCalled()
})
it('muestra los rechazos del servidor y permite buscar restauraciones realizadas', async () => {
  mocks.restaurar.mockRejectedValue({ response: { data: { detail: 'El cambio ya fue restaurado.' } } })
  render(<RestaurarCambiosPanel />)
  fireEvent.click(await screen.findByRole('button', { name: 'Revisar restauración' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Confirmar restauración' }))
  expect((await screen.findByRole('alert')).textContent).toContain('ya fue restaurado')
  fireEvent.change(screen.getByLabelText('Buscar cambio'), { target: { value: '323 BIS' } })
  fireEvent.click(screen.getByRole('button', { name: 'Buscar' }))
  fireEvent.change(screen.getByLabelText('Estado'), { target: { value: 'revertido' } })
  await waitFor(() => expect(mocks.grupos).toHaveBeenLastCalledWith({ estado_revision: 'revertido', operaciones: 'deroga,abroga', page: 1, buscar: '323 BIS' }))
})
