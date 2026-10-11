import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import CasosPage from './CasosPage'
import useCasos from '../hooks/useCasos'
import casosApi from '../../../api/casosApi'
import { dialogs } from '../../../components/ui/dialogs'

const estado = vi.hoisted(() => ({ escribir: true, navigate: vi.fn() }))
vi.mock('react-router-dom', () => ({ useNavigate: () => estado.navigate }))
vi.mock('../hooks/useCasos', () => ({ default: vi.fn() }))
vi.mock('../../auth/store/authStore', () => ({ default: selector => selector({ puedeEscribir: () => estado.escribir }) }))
vi.mock('../../../api/casosApi', () => ({ default: { eliminar: vi.fn() } }))
vi.mock('../../../components/ui/dialogs', () => ({ dialogs: { confirm: vi.fn() } }))

const caso = { id: '10000000-0000-4000-8000-000000000001', codigo: 'CASO-PRUEBA', titulo: 'Caso de prueba', cliente_nombre: 'Cliente de prueba', etapa: 'registrado' }
let listado
beforeEach(() => {
  vi.clearAllMocks()
  estado.escribir = true
  listado = { casos: [caso], loading: false, error: null, page: 1, setPage: vi.fn(), totalPages: 1, count: 1,
    filtros: {}, setFiltros: vi.fn(), limpiarFiltros: vi.fn(), reload: vi.fn().mockResolvedValue() }
  useCasos.mockReturnValue(listado)
  casosApi.eliminar.mockResolvedValue({})
  dialogs.confirm.mockResolvedValue(true)
})
afterEach(cleanup)
const boton = () => screen.getByRole('button', { name: 'Eliminar caso Caso de prueba' })

it('conserva las tarjetas y elimina con confirmación sin abrir el detalle', async () => {
  render(<CasosPage />)
  expect(screen.getByText('Cliente de prueba')).toBeTruthy()
  expect(screen.getByText('Sin PDF')).toBeTruthy()
  fireEvent.click(boton())
  await waitFor(() => expect(listado.reload).toHaveBeenCalledTimes(1))
  expect(dialogs.confirm.mock.calls[0][0]).toContain('Caso de prueba')
  expect(casosApi.eliminar).toHaveBeenCalledWith(caso.id)
  expect(estado.navigate).not.toHaveBeenCalled()
})
it('cancelar no elimina ni recarga', async () => {
  dialogs.confirm.mockResolvedValue(false)
  render(<CasosPage />)
  fireEvent.click(boton())
  await waitFor(() => expect(dialogs.confirm).toHaveBeenCalledTimes(1))
  expect(casosApi.eliminar).not.toHaveBeenCalled()
  expect(listado.reload).not.toHaveBeenCalled()
})
it('los lectores no tienen eliminación rápida', () => {
  estado.escribir = false
  render(<CasosPage />)
  expect(screen.queryByRole('button', { name: /Eliminar caso/ })).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: /Ver detalles/ }))
  expect(estado.navigate).toHaveBeenCalledWith(`/casos/${caso.id}`)
})
it('muestra el error y conserva el listado cuando la API rechaza la eliminación', async () => {
  casosApi.eliminar.mockRejectedValue({ response: { data: { detail: 'No tienes permiso.' } } })
  render(<CasosPage />)
  fireEvent.click(boton())
  await waitFor(() => expect(screen.getByRole('alert').textContent).toBe('No tienes permiso.'))
  expect(listado.reload).not.toHaveBeenCalled()
  expect(screen.getByText('Cliente de prueba')).toBeTruthy()
  expect(boton().disabled).toBe(false)
})
it('evita confirmaciones y solicitudes duplicadas mientras elimina', async () => {
  let resolver
  casosApi.eliminar.mockReturnValue(new Promise(resolve => { resolver = resolve }))
  render(<CasosPage />)
  fireEvent.click(boton())
  fireEvent.click(boton())
  await waitFor(() => expect(boton().disabled).toBe(true))
  expect(dialogs.confirm).toHaveBeenCalledTimes(1)
  expect(casosApi.eliminar).toHaveBeenCalledTimes(1)
  resolver({})
  await waitFor(() => expect(boton().disabled).toBe(false))
})
it('vuelve a la página anterior al eliminar el último caso de una página posterior', async () => {
  listado.page = 2
  listado.totalPages = 2
  render(<CasosPage />)
  fireEvent.click(boton())
  await waitFor(() => expect(listado.setPage).toHaveBeenCalledWith(1))
  expect(listado.reload).not.toHaveBeenCalled()
})
it('la tarjeta puede abrirse con el teclado sin interferir con sus botones', () => {
  render(<CasosPage />)
  const tarjeta = screen.getByText('CASO-PRUEBA').closest('[role="button"]')
  fireEvent.keyDown(tarjeta, { key: 'Enter' })
  expect(estado.navigate).toHaveBeenCalledWith(`/casos/${caso.id}`)
  estado.navigate.mockClear()
  fireEvent.keyDown(boton(), { key: 'Enter' })
  expect(estado.navigate).not.toHaveBeenCalled()
})
