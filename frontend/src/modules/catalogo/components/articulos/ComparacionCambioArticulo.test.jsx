import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import ComparacionCambioArticulo from './ComparacionCambioArticulo'
afterEach(cleanup)
const parcial = { operacion: 'deroga', aplicado: true, texto_antes: 'I. Vigente.\nIII. Texto retirado.', texto_despues: 'I. Vigente.',
  parte_afectada: { tipo: 'parcial', descripcion: 'Parágrafo III', partes: [{ fragmento: 'III. Texto retirado.' }] } }
it('marca exactamente la parte retirada y conserva el resto sin tachar', () => {
  const { container } = render(<ComparacionCambioArticulo registro={parcial} />)
  expect(container.querySelector('del').textContent).toBe('III. Texto retirado.')
  expect(screen.getByRole('region', { name: 'Texto antes del cambio' }).querySelector('pre').textContent).toBe(parcial.texto_antes)
  expect(screen.getByRole('region', { name: 'Texto después del cambio' }).querySelector('pre').textContent).toBe(parcial.texto_despues)
})
it('diferencia la derogación total aunque los textos sean iguales, sin simular un borrado', () => {
  const { container } = render(<ComparacionCambioArticulo registro={{ operacion: 'deroga', aplicado: true, texto_antes: 'Texto conservado.', texto_despues: 'Texto conservado.', parte_afectada: { tipo: 'total' } }} />)
  expect(screen.getByText('Derogación total confirmada')).toBeTruthy()
  expect(screen.getByText('Sin esta confirmación registrada')).toBeTruthy()
  expect(screen.getByText('El cambio está en la vigencia, no en el texto reproducido.')).toBeTruthy()
  expect(container.querySelector('del')).toBeNull()
})
it('resalta el fragmento que se recuperaría al restaurar', () => {
  const { container } = render(<ComparacionCambioArticulo registro={parcial} restaurar />)
  expect(container.querySelector('ins').textContent).toBe('III. Texto retirado.')
  expect(screen.getByText('Se recuperaría la parte retirada: Parágrafo III.')).toBeTruthy()
})
it('presenta las fechas futuras como comparación prevista', () => {
  render(<ComparacionCambioArticulo registro={{ ...parcial, aplicado: false }} />)
  expect(screen.getByText('Después previsto')).toBeTruthy()
  expect(screen.getByText('Derogación parcial programada')).toBeTruthy()
})
