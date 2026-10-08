import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import DocumentosPage from './DocumentosPage'
import catalogoApi from '../../../api/catalogoApi'
import { dialogs } from '../../../components/ui/dialogs'
import { descargarBlob } from '../utils/descargas'

vi.mock('../../../api/catalogoApi', () => ({ default: {
  normas: vi.fn(), ramas: vi.fn(), listarDocumentosNorma: vi.fn(),
  descargarDocumentoNorma: vi.fn(), eliminarDocumentoNorma: vi.fn(),
} }))
vi.mock('../utils/descargas', () => ({ descargarBlob: vi.fn(), formatTamano: (v) => `${v} B` }))
let admin = true
let escribir = true
vi.mock('../../auth/store/authStore', () => ({ default: (selector) => selector({
  isAdmin: () => admin, puedeEscribir: () => escribir,
}) }))
const documento = { id: 8, nombre_original: 'norma.pdf', norma_nombre: 'Código de prueba',
  rama_nombre: 'Penal', vigente: true, tamano: 100, created_at: '2026-10-08T12:00:00Z' }
beforeEach(() => {
  vi.clearAllMocks()
  admin = true
  escribir = true
  catalogoApi.normas.mockResolvedValue({ data: [{ id: 1, nombre: 'Código de prueba' }] })
  catalogoApi.ramas.mockResolvedValue({ data: [{ id: 2, nombre: 'Penal' }] })
  catalogoApi.listarDocumentosNorma.mockResolvedValue({ data: { results: [documento], count: 30 } })
  vi.spyOn(dialogs, 'confirm').mockResolvedValue(true)
})
afterEach(() => { cleanup(); vi.restoreAllMocks() })
const montar = () => render(<MemoryRouter><DocumentosPage /></MemoryRouter>)

it('permite consultar y descargar a lectores y oculta carga y eliminación', async () => {
  admin = false
  escribir = false
  const blob = new Blob(['pdf'])
  catalogoApi.descargarDocumentoNorma.mockResolvedValue({ data: blob })
  montar()
  await screen.findByText('norma.pdf')
  expect(screen.queryByRole('link', { name: 'Cargar PDF de norma' })).toBeNull()
  expect(screen.queryByRole('button', { name: 'Eliminar norma.pdf' })).toBeNull()
  expect(screen.getByRole('button', { name: 'Ver PDF norma.pdf' })).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Descargar norma.pdf' }))
  await waitFor(() => expect(descargarBlob).toHaveBeenCalledWith(blob, 'norma.pdf'))
})

it('envía filtros al servidor y vuelve a la primera página al buscar', async () => {
  montar()
  await screen.findByText('norma.pdf')
  expect(screen.getByRole('link', { name: 'Cargar PDF de norma' }).getAttribute('href')).toBe('/catalogo/cargar')
  fireEvent.click(screen.getByRole('button', { name: 'Página siguiente' }))
  await waitFor(() => expect(catalogoApi.listarDocumentosNorma).toHaveBeenLastCalledWith(
    expect.objectContaining({ page: 2, page_size: 25 }), expect.any(AbortSignal)))
  fireEvent.change(screen.getByLabelText('Buscar documento o norma'), { target: { value: 'penal' } })
  fireEvent.change(screen.getByLabelText('Norma'), { target: { value: '1' } })
  fireEvent.change(screen.getByLabelText('Rama'), { target: { value: '2' } })
  fireEvent.change(screen.getByLabelText('Versión del archivo'), { target: { value: 'false' } })
  await waitFor(() => expect(catalogoApi.listarDocumentosNorma).toHaveBeenLastCalledWith(
    { page: 1, page_size: 25, search: 'penal', norma_id: '1', rama_id: '2', vigente: 'false' }, expect.any(AbortSignal)))
})

it('respeta la cancelación y muestra el rechazo al borrar un PDF histórico', async () => {
  dialogs.confirm.mockResolvedValueOnce(false)
  catalogoApi.eliminarDocumentoNorma.mockRejectedValue({ response: { data: { detail: 'Este PDF respalda avisos o versiones históricas y debe conservarse.' } } })
  montar()
  await screen.findByText('norma.pdf')
  fireEvent.click(screen.getByRole('button', { name: 'Eliminar norma.pdf' }))
  await waitFor(() => expect(dialogs.confirm).toHaveBeenCalledTimes(1))
  expect(catalogoApi.eliminarDocumentoNorma).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Eliminar norma.pdf' }))
  expect(await screen.findByText('Este PDF respalda avisos o versiones históricas y debe conservarse.')).toBeTruthy()
})

it('actualiza el listado después de eliminar', async () => {
  catalogoApi.eliminarDocumentoNorma.mockResolvedValue({})
  montar()
  await screen.findByText('norma.pdf')
  catalogoApi.listarDocumentosNorma.mockResolvedValue({ data: { results: [], count: 0 } })
  fireEvent.click(screen.getByRole('button', { name: 'Eliminar norma.pdf' }))
  expect(await screen.findByText('No hay documentos que coincidan con los filtros.')).toBeTruthy()
  expect(catalogoApi.eliminarDocumentoNorma).toHaveBeenCalledWith(8)
})
