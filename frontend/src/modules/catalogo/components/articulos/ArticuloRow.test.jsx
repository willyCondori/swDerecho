import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import ArticuloRow from './ArticuloRow'
import { MemoryRouter } from 'react-router-dom'

it('oculta todo el contenido y permite mostrarlo y ocultarlo sin duplicar el texto', () => {
  const contenido = 'Texto jurídico completo. '.repeat(100)
  const articulo = { id: 7, numero_articulo: '7', titulo: 'Artículo de prueba', contenido }
  const { container } = render(<table><tbody><ArticuloRow articulo={articulo} busqueda="jurídico" /></tbody></table>)
  const texto = container.querySelector('[class*="articleText"]')
  expect(texto.textContent).toBe('')
  expect(texto.hidden).toBe(true)
  expect(screen.queryByRole('button', { name: 'Copiar artículo' })).toBeNull()
  expect(screen.queryByRole('button', { name: 'PDF original' })).toBeNull()
  expect(screen.getByRole('button', { name: 'Ver más' }).getAttribute('aria-expanded')).toBe('false')
  fireEvent.click(screen.getByRole('button', { name: 'Ver más' }))
  expect(container.querySelector('[class*="articleText"]').textContent).toBe(contenido)
  expect(container.querySelectorAll('[class*="articleText"]')).toHaveLength(1)
  expect(container.querySelectorAll('mark')).toHaveLength(100)
  const copiar = screen.getByRole('button', { name: 'Copiar artículo' })
  expect(texto.compareDocumentPosition(copiar) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(screen.getByRole('button', { name: 'PDF original' })).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Ver menos' }).getAttribute('aria-expanded')).toBe('true')
  fireEvent.click(screen.getByRole('button', { name: 'Ver menos' }))
  expect(texto.textContent).toBe('')
  expect(texto.hidden).toBe(true)
  expect(screen.queryByRole('button', { name: 'Copiar artículo' })).toBeNull()
  expect(screen.queryByRole('button', { name: 'PDF original' })).toBeNull()
  expect(container.querySelectorAll('[class*="articleText"]')).toHaveLength(1)
})

it('copia el contenido original, incluidos saltos de línea e incisos', async () => {
  const writeText = vi.fn().mockResolvedValue()
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
  const contenido = 'ARTÍCULO 1.\nI. Primer inciso.\nII. Segundo inciso.'
  render(<table><tbody><ArticuloRow articulo={{ id: 1, numero_articulo: '1', contenido }} /></tbody></table>)
  fireEvent.click(screen.getAllByRole('button', { name: 'Ver más' }).at(-1))
  fireEvent.click(screen.getAllByRole('button', { name: 'Copiar artículo' }).at(-1))
  await waitFor(() => expect(writeText).toHaveBeenCalledWith(contenido))
  expect(await screen.findByText('Artículo copiado')).toBeTruthy()
})

it('muestra un acceso breve a los avisos sin repetir su fundamento en la tabla', () => {
  render(<MemoryRouter><table><tbody><ArticuloRow articulo={{ id: 88, numero_articulo: '323 BIS', estado_vigencia: 'derogado_parcialmente',
    contenido: 'I. Texto vigente.', avisos_vigencia: [{ id: 1, estado: 'confirmado', operacion: 'deroga', mensaje: 'Fundamento repetido de la ley.', cita: 'Texto de la disposición derogatoria.' }] }} /></tbody></table></MemoryRouter>)
  expect(screen.getByRole('link', { name: 'Consultar avisos de este artículo' }).getAttribute('href')).toBe('/catalogo/avisos?articulo=88')
  expect(screen.queryByText('Fundamento repetido de la ley.')).toBeNull()
  expect(screen.queryByText('Texto de la disposición derogatoria.')).toBeNull()
})
