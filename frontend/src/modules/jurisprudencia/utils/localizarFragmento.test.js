import { expect, it } from 'vitest'
import localizarFragmento from './localizarFragmento'

it('localiza el fragmento literal y conserva todos los caracteres originales', () => {
  const texto = 'Encabezado\n\nEl delito de robo agravado.\n\nDecisión.'
  const rango = localizarFragmento(texto, 'El delito de robo agravado.')
  expect(texto.slice(rango.inicio, rango.fin)).toBe('El delito de robo agravado.')
  expect(texto.slice(0, rango.inicio) + texto.slice(rango.inicio, rango.fin) + texto.slice(rango.fin)).toBe(texto)
})

it('tolera saltos de línea y trata signos jurídicos como texto literal', () => {
  const texto = 'Inicio. Art. 332 (1) [CP].\n\nRobo\n agravado. Fin.'
  const rango = localizarFragmento(texto, 'Art. 332 (1) [CP]. Robo agravado.')
  expect(texto.slice(rango.inicio, rango.fin)).toBe('Art. 332 (1) [CP].\n\nRobo\n agravado.')
})

it('no destaca palabras aisladas cuando falta el fragmento completo', () => {
  expect(localizarFragmento('Existe un robo.', 'El secuestro exige privación de libertad.')).toBeNull()
  expect(localizarFragmento('Robo agravado.', ' ')).toBeNull()
  expect(localizarFragmento(undefined, 'Robo')).toBeNull()
})
