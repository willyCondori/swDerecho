import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import ArticuloRow from './ArticuloRow'
import catalogoApi from '../../../../api/catalogoApi'

vi.mock('../../../../api/catalogoApi', () => ({ default: { articulo: vi.fn() } }))

const articulo = { id: 7, numero_articulo: '7', titulo: 'Artículo de prueba', contenido_preview: 'Vista previa' }
const fila = (isExpanded) => <table><tbody><ArticuloRow articulo={articulo} isExpanded={isExpanded} onToggleExpand={() => {}} /></tbody></table>

beforeEach(() => vi.clearAllMocks())

it('solicita el texto completo solo al expandir y lo reutiliza al reabrir', async () => {
  catalogoApi.articulo.mockResolvedValue({ data: { contenido: 'Texto legal completo' } })
  const { rerender } = render(fila(false))
  expect(catalogoApi.articulo).not.toHaveBeenCalled()
  rerender(fila(true))
  await screen.findByText('Texto legal completo')
  expect(catalogoApi.articulo).toHaveBeenCalledWith(7)
  rerender(fila(false))
  rerender(fila(true))
  expect(catalogoApi.articulo).toHaveBeenCalledTimes(1)
})

it('permite reintentar si falla el detalle', async () => {
  catalogoApi.articulo.mockRejectedValueOnce(new Error('red')).mockResolvedValueOnce({ data: { contenido: 'Recuperado' } })
  render(fila(true))
  await screen.findByRole('alert')
  fireEvent.click(screen.getByText('Reintentar'))
  await waitFor(() => expect(screen.getByText('Recuperado')).toBeTruthy())
})
