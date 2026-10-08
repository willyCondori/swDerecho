import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import CasoDetailPage from './CasoDetailPage'
import useCasoDetail from '../hooks/useCasoDetail'

vi.mock('../hooks/useCasoDetail', () => ({ default: vi.fn() }))
vi.mock('../../auth/store/authStore', () => ({ default: (selector) => selector({ puedeEscribir: () => false, isAdmin: () => false }) }))
vi.mock('../../documentos/components/DocumentosCasoList', () => ({ default: () => null }))
afterEach(cleanup)

it('identifica las sugerencias complementarias y muestra fallos de OCR a lectores', () => {
  useCasoDetail.mockReturnValue({ caso: { codigo: 'C-1', titulo: 'Caso', etapa: 'abierto',
    estado_analisis: 'error', analisis_error: 'No se pudo extraer el texto del PDF del caso.' },
    articulos: [
      { id: 1, es_sugerencia: false, articulo: { numero_articulo: '10', norma_sigla: 'CP', contenido: 'Artículo principal.' } },
      { id: 2, es_sugerencia: true, articulo: { numero_articulo: '8', norma_sigla: 'CP', contenido: 'Tentativa complementaria.' } },
    ], loading: false,
  })
  render(<MemoryRouter><CasoDetailPage /></MemoryRouter>)
  expect(screen.getByRole('alert').textContent).toContain('No se pudo extraer el texto del PDF del caso.')
  const items = screen.getAllByRole('listitem')
  expect(within(items[0]).queryByText('Sugerencia complementaria')).toBeNull()
  expect(within(items[1]).getByText('Sugerencia complementaria')).toBeTruthy()
})
