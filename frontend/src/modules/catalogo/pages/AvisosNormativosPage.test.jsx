import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import AvisosNormativosPage from './AvisosNormativosPage'
const mocks = vi.hoisted(() => ({ grupos: vi.fn() }))
vi.mock('../../../api/normativaApi', () => ({ default: { gruposAvisos: mocks.grupos } }))
vi.mock('../../../api/catalogoApi', () => ({ default: { normas: vi.fn().mockResolvedValue({ data: [{ id: 5, nombre: 'Código Penal' }] }) } }))
vi.mock('../../auth/store/authStore', () => ({ default: (selector) => selector({ isAdmin: () => false }) }))
beforeEach(() => {
  vi.clearAllMocks()
  const base = { estado_revision: 'pendiente', operacion: 'deroga', destino_catalogo: { encontrado: true }, aviso: { categoria_aviso: 'deroga' } }
  mocks.grupos.mockResolvedValue({ data: { count: 1, results: [{ id: 1, norma_causante: 'LEY 1636', disposicion_fuente: 'disposición derogatoria única', fecha: '2025-09-10',
    cita: 'Se derogan el parágrafo III del artículo 323 Bis y el artículo 281 Quater.', afectaciones: [
      { ...base, id: 1, referencia: { norma: 'Código Penal', unidad: '323 BIS', alcance: 'Parágrafo III' } },
      { ...base, id: 2, referencia: { norma: 'Código Penal', unidad: '281 QUATER', alcance: 'total' } },
    ] }], next: null } })
})
afterEach(cleanup)
it('muestra un fundamento por disposición y conserva sus dos destinos', async () => {
  render(<MemoryRouter><AvisosNormativosPage /></MemoryRouter>)
  expect(await screen.findByText('LEY 1636 · disposición derogatoria única')).toBeTruthy()
  expect(screen.getAllByText('Se derogan el parágrafo III del artículo 323 Bis y el artículo 281 Quater.')).toHaveLength(1)
  expect(screen.getByText(/Artículo 323 BIS/)).toBeTruthy()
  expect(screen.getByText(/Artículo 281 QUATER/)).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Revisar este destino' })).toBeNull()
  expect(screen.getByRole('status').textContent).toContain('1 fundamentos encontrados')
})
it('busca en el servidor y permite filtrar por tipo y estado', async () => {
  render(<MemoryRouter><AvisosNormativosPage /></MemoryRouter>)
  await screen.findByText('LEY 1636 · disposición derogatoria única')
  fireEvent.change(screen.getByLabelText('Buscar aviso'), { target: { value: 'Ley 1636' } })
  await waitFor(() => expect(mocks.grupos).toHaveBeenLastCalledWith({ buscar: 'Ley 1636' }))
  fireEvent.change(screen.getByLabelText('Tipo de aviso'), { target: { value: 'deroga' } })
  fireEvent.change(screen.getByLabelText('Estado de revisión'), { target: { value: 'pendiente' } })
  await waitFor(() => expect(mocks.grupos).toHaveBeenLastCalledWith({ buscar: 'Ley 1636', tipo: 'deroga', estado_revision: 'pendiente' }))
})
it('abre el contexto del artículo desde la tabla y permite limpiar todos los filtros', async () => {
  render(<MemoryRouter initialEntries={['/catalogo/avisos?articulo=88']}><AvisosNormativosPage /></MemoryRouter>)
  await waitFor(() => expect(mocks.grupos).toHaveBeenCalledWith({ articulo: '88' }))
  fireEvent.click(screen.getByRole('button', { name: 'Limpiar filtros' }))
  await waitFor(() => expect(mocks.grupos).toHaveBeenLastCalledWith({}))
})
