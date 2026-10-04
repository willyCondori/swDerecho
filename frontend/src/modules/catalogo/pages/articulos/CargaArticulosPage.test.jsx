import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import useAuthStore from '../../../auth/store/authStore'
import CargaArticulosPage from './CargaArticulosPage'
vi.mock('../../hooks/useCargaArticulos', () => ({ useCargaArticulos: () => ({
  jerarquias: [{ id: 1, nombre: 'Ley', nivel: 1 }], ramas: [{ id: 2, nombre: 'Penal' }, { id: 3, nombre: 'Civil' }],
  normas: [{ id: 7, nombre: 'Código Penal', ramas: [{ id: 2, nombre: 'Penal' }] }, { id: 8, nombre: 'Norma múltiple', ramas: [{ id: 2 }, { id: 3 }] }, { id: 9, nombre: 'Código Penal Boliviano', sigla: 'CP' }],
  loadingOpts: false, cargar: vi.fn(), reset: vi.fn(), enviando: false, procesando: false, resumen: null, error: null,
  advertencias: [], otrasCargas: [], verificandoCargas: false,
}) }))
vi.mock('../../hooks/useRevisionPdf', () => ({ useRevisionPdf: () => ({ revision: null, revisando: false, limpiarRevision: vi.fn(), revisarPdf: vi.fn() }) }))
vi.mock('../../components/articulos/GacetaPanel', () => ({ default: () => null }))
let usuario = 200
beforeEach(() => useAuthStore.setState({ user: { id: ++usuario } }))
afterEach(cleanup)
it('conserva los campos y el PDF elegido al salir y volver y los limpia al solicitarlo', () => {
  const vista = render(<CargaArticulosPage />)
  fireEvent.change(screen.getByLabelText('Nombre del documento'), { target: { value: 'Ley pendiente' } })
  fireEvent.change(screen.getByLabelText('Rama de derecho'), { target: { value: '2' } })
  fireEvent.change(vista.container.querySelector('input[type=file]'), { target: { files: [new File(['pdf'], 'pendiente.pdf', { type: 'application/pdf' })] } })
  vista.unmount()
  render(<CargaArticulosPage />)
  expect(screen.getByLabelText('Nombre del documento').value).toBe('Ley pendiente')
  expect(screen.getByLabelText('Rama de derecho').value).toBe('2')
  expect(screen.getByText('pendiente.pdf')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Limpiar' }))
  expect(screen.getByLabelText('Nombre del documento').value).toBe('')
  expect(screen.queryByText('pendiente.pdf')).toBeNull()
})
it('selecciona la rama de la norma existente y no adivina entre varias ramas', () => {
  render(<CargaArticulosPage />)
  fireEvent.click(screen.getByRole('tab', { name: 'Norma existente' }))
  fireEvent.change(screen.getByLabelText('Norma'), { target: { value: '7' } })
  expect(screen.getByLabelText('Rama de derecho').value).toBe('2')
  fireEvent.change(screen.getByLabelText('Norma'), { target: { value: '8' } })
  expect(screen.getByLabelText('Rama de derecho').value).toBe('')
  expect(screen.getByText(/asociada a varias ramas/)).toBeTruthy()
})
it('descarta el borrador al cambiar de usuario', () => {
  const vista = render(<CargaArticulosPage />)
  fireEvent.change(screen.getByLabelText('Nombre del documento'), { target: { value: 'Borrador anterior' } })
  act(() => useAuthStore.setState({ user: { id: ++usuario } }))
  expect(screen.getByLabelText('Nombre del documento').value).toBe('')
  vista.unmount()
})

it('completa Penal aunque el listado del Código Penal todavía no incluya ramas', () => {
  render(<CargaArticulosPage />)
  fireEvent.click(screen.getByRole('tab', { name: 'Norma existente' }))
  fireEvent.change(screen.getByLabelText('Rama de derecho'), { target: { value: '3' } })
  fireEvent.change(screen.getByLabelText('Norma'), { target: { value: '9' } })
  expect(screen.getByLabelText('Rama de derecho').value).toBe('2')
})
