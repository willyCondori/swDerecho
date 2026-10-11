import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import JurisprudenciaPage from './JurisprudenciaPage'
import TSJPage from './TSJPage'
import jurisprudenciaApi from '../../../api/jurisprudenciaApi'

const permisos = vi.hoisted(() => ({ escritura: true }))
vi.mock('../../auth/store/authStore', () => ({ default: (selector) => selector({ puedeEscribir: () => permisos.escritura }) }))
vi.mock('../../../api/jurisprudenciaApi', () => ({ default: {
  listar: vi.fn(), resumen: vi.fn(), obtener: vi.fn(), buscarTSJ: vi.fn(), incorporar: vi.fn(), estado: vi.fn(),
} }))
const RESOLUCION = { id: 1, fuente_id: '123', numero: 'AS/123/2024', fecha: '2024-01-15', sala: 'Sala Penal', extracto: 'Extracto de prueba', indexada: true }
beforeEach(() => {
  vi.clearAllMocks(); sessionStorage.clear(); permisos.escritura = true
  jurisprudenciaApi.listar.mockResolvedValue({ data: { results: [RESOLUCION], count: 30 } })
  jurisprudenciaApi.resumen.mockResolvedValue({ data: { resoluciones: 30, indexadas: 25, embeddings: 500, salas: ['Sala Penal'], departamentos: ['La Paz'] } })
  jurisprudenciaApi.obtener.mockResolvedValue({ data: { ...RESOLUCION, texto: 'Texto completo sobre los hechos y la decisión.', url_fuente: 'https://apigenesis.tsj.bo/api/v1/resoluciones/123' } })
  jurisprudenciaApi.buscarTSJ.mockResolvedValue({ data: { results: [{ ...RESOLUCION, registro_id: null }], count: 1, total_pages: 1 } })
})
afterEach(cleanup)

it('permite filtrar y paginar la jurisprudencia guardada', async () => {
  render(<MemoryRouter><JurisprudenciaPage /></MemoryRouter>)
  expect(await screen.findByText('AS/123/2024')).toBeTruthy()
  expect(screen.queryByText('Disponibles para análisis IA')).toBeNull()
  expect(screen.queryByText('Fragmentos indexados')).toBeNull()
  expect(screen.queryByText(/Los contadores se actualizan/)).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Actualizar listado' }))
  await waitFor(() => expect(jurisprudenciaApi.resumen).toHaveBeenCalledTimes(2))
  fireEvent.change(screen.getByLabelText('Buscar por texto, número o expediente'), { target: { value: 'robo' } })
  fireEvent.click(screen.getByRole('button', { name: 'Buscar', exact: true }))
  await waitFor(() => expect(jurisprudenciaApi.listar).toHaveBeenLastCalledWith(expect.objectContaining({ search: 'robo', page: 1 }), expect.any(Object)))
  fireEvent.click(screen.getByRole('button', { name: 'Página siguiente' }))
  await waitFor(() => expect(jurisprudenciaApi.listar).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 }), expect.any(Object)))
})

it('abre el lector dentro del sistema desde un resultado de caso', async () => {
  render(<MemoryRouter initialEntries={['/jurisprudencia?resolucion=1']}><JurisprudenciaPage /></MemoryRouter>)
  expect(await screen.findByText('Texto completo sobre los hechos y la decisión.')).toBeTruthy()
  expect(screen.getByRole('dialog')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Cerrar ventana' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
})

it('busca en el TSJ y permite al abogado incorporar una resolución', async () => {
  jurisprudenciaApi.incorporar.mockResolvedValue({ data: { task_id: 'tsj-1' } })
  jurisprudenciaApi.estado.mockResolvedValue({ data: { estado: 'SUCCESS', resultado: { registro_id: 1 } } })
  render(<MemoryRouter><TSJPage /></MemoryRouter>)
  fireEvent.click(await screen.findByRole('button', { name: 'Incorporar jurisprudencia' }))
  expect(await screen.findByText('Resolución guardada y disponible para el análisis IA.')).toBeTruthy()
  expect(jurisprudenciaApi.incorporar).toHaveBeenCalledWith('123')
  await waitFor(() => expect(jurisprudenciaApi.buscarTSJ).toHaveBeenCalledTimes(2))
})

it('permite búsqueda al asistente y muestra una falla del TSJ', async () => {
  permisos.escritura = false
  render(<MemoryRouter><TSJPage /></MemoryRouter>)
  expect(await screen.findByText('AS/123/2024')).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Incorporar jurisprudencia' })).toBeNull()
  jurisprudenciaApi.buscarTSJ.mockRejectedValueOnce({ response: { data: { detail: 'TSJ temporalmente no disponible.' } } })
  fireEvent.change(screen.getByLabelText('Palabras de búsqueda en el TSJ'), { target: { value: 'robo' } })
  fireEvent.click(screen.getByRole('button', { name: 'Buscar en el TSJ' }))
  expect(await screen.findByText('TSJ temporalmente no disponible.')).toBeTruthy()
})
