import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import ArticuloRow from './ArticuloRow'

it('muestra el artículo completo al expandir sin truncarlo a 360 caracteres', () => {
  const contenido = 'Texto jurídico completo. '.repeat(100)
  const articulo = { id: 7, numero_articulo: '7', titulo: 'Artículo de prueba', contenido }
  const toggle = vi.fn()
  const fila = (expandida) => <table><tbody><ArticuloRow articulo={articulo} isExpanded={expandida} onToggleExpand={toggle} /></tbody></table>
  const { container, rerender } = render(fila(false))
  fireEvent.click(screen.getByRole('button', { name: '▼ Ver completo' }))
  expect(toggle).toHaveBeenCalledWith(7)
  rerender(fila(true))
  expect(container.querySelector('pre').textContent).toBe(contenido)
})
