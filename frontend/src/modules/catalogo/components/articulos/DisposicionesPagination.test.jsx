import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import DisposicionesList from './DisposicionesList'
import DisposicionesTable from './DisposicionesTable'
const get = vi.hoisted(() => vi.fn())
vi.mock('../../../../api/axiosInstance', () => ({ default: { get } }))
afterEach(() => { cleanup(); vi.clearAllMocks() })

it('pagina las disposiciones del PDF, cambia tamaño y reinicia al cambiar el documento', () => {
  const rows = Array.from({ length: 23 }, (_, index) => ({ key: index, tipo: 'final', numero: `DF ${index + 1}`, texto: `Texto ${index + 1}` }))
  const { container, rerender } = render(<DisposicionesList rows={rows} />)
  expect(container.querySelectorAll('tbody tr')).toHaveLength(10)
  fireEvent.click(screen.getByLabelText('Página siguiente'))
  expect(screen.getByText('DF 11')).toBeTruthy()
  expect(screen.queryByText('DF 1')).toBeNull()
  fireEvent.click(screen.getByLabelText('Última página'))
  expect(container.querySelectorAll('tbody tr')).toHaveLength(3)
  expect(screen.getByLabelText('Página siguiente').disabled).toBe(true)
  fireEvent.change(screen.getByLabelText('Disposiciones por página'), { target: { value: '25' } })
  expect(container.querySelectorAll('tbody tr')).toHaveLength(23)
  rerender(<DisposicionesList rows={rows.slice(0, 2)} />)
  expect(screen.getByText('Mostrando 1–2 de 2 disposiciones')).toBeTruthy()
})

it('usa la página del servidor sin paginarla dos veces y reinicia los filtros', async () => {
  get.mockImplementation((url, { params }) => Promise.resolve({ data: { count: 12,
    results: Array.from({ length: params.page === 1 ? 10 : 2 }, (_, index) => ({ id: index,
      norma_id: 5, norma_nombre: 'Ley', tipo: 'final', numero: `DD ${params.page}-${index}`, contenido: 'Texto' })) } }))
  const { container, rerender } = render(<MemoryRouter><DisposicionesTable normaId={5} /></MemoryRouter>)
  await screen.findByText('Mostrando 1–10 de 12 disposiciones')
  fireEvent.click(screen.getByLabelText('Página siguiente'))
  await screen.findByText('Mostrando 11–12 de 12 disposiciones')
  expect(container.querySelectorAll('tbody tr')).toHaveLength(2)
  expect(get).toHaveBeenLastCalledWith('/api/catalogo/disposiciones/', { params: { norma_id: 5, rama_id: undefined, page: 2, page_size: 10 } })
  rerender(<MemoryRouter><DisposicionesTable normaId={6} /></MemoryRouter>)
  await waitFor(() => expect(get).toHaveBeenLastCalledWith('/api/catalogo/disposiciones/', { params: { norma_id: 6, rama_id: undefined, page: 1, page_size: 10 } }))
})
