import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import CambiosNormativosPanel from './CambiosNormativosPanel'
const mocks = vi.hoisted(() => ({ cambios: vi.fn() }))
vi.mock('../../../../api/normativaApi', () => ({ default: { cambios: mocks.cambios } }))
vi.mock('../../../../api/catalogoApi', () => ({ default: { normas: vi.fn().mockResolvedValue({ data: [] }) } }))
afterEach(cleanup)
it('comparte fundamento sin fusionar los destinos y distingue las notas históricas', async () => {
  const base = { fuente: 1, norma_causante: 'Ley 1636', unidad_fuente: 'DD ÚNICA', disposicion_fuente: 'disposición derogatoria única',
    fecha_norma_causante: '2025-09-10', estado_revision: 'pendiente', origen: 'clausula', operacion: 'deroga',
    cita: 'Se derogan el parágrafo III del 323 Bis y el 281 Quater.', destino_catalogo: { encontrado: true } }
  mocks.cambios.mockResolvedValue({ data: { results: [
    { ...base, id: 1, referencia: { norma: 'Código Penal', unidad: '323 BIS', alcance: 'Parágrafo III' } },
    { ...base, id: 2, referencia: { norma: 'Código Penal', unidad: '281 QUATER', alcance: 'total' } },
    { ...base, id: 3, unidad_fuente: '179', operacion: 'modifica', cita: 'Modificado por Ley 037.',
      referencia: { unidad: '179', alcance: 'total' }, aviso: { nota_historica: true, mensaje: 'Texto ya incorporado al PDF.' } },
  ] } })
  render(<CambiosNormativosPanel />)
  await waitFor(() => expect(screen.getAllByRole('button', { name: 'Confirmar derogación' })).toHaveLength(2))
  expect(screen.getAllByText(base.cita)).toHaveLength(1)
  expect(screen.getByText(/323 BIS/)).toBeTruthy()
  expect(screen.getByText(/281 QUATER/)).toBeTruthy()
  expect(screen.getByText('Nota histórica del texto incorporado')).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Confirmar afectación' })).toBeNull()
})
