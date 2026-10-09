import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import JurisprudenciaRelacionada from './JurisprudenciaRelacionada'
import casosApi from '../../../api/casosApi'

vi.mock('../../../api/casosApi', () => ({ default: { jurisprudencia: vi.fn() } }))
afterEach(() => { cleanup(); vi.clearAllMocks() })

it('muestra resolución, fragmento y fuente al terminar el análisis', async () => {
  casosApi.jurisprudencia.mockResolvedValue({ data: { estado: 'completado', resultados: [{
    id: 1, fuente_id: '100', numero: 'AS/100/2024', fecha: '2024-02-29', sala: 'Sala Penal',
    score_semantico: 0.85, fragmento: 'El Tribunal examinó la prueba del robo.',
    url_fuente: 'https://apigenesis.tsj.bo/api/v1/resoluciones/100', desactualizada: true,
  }] } })
  render(<JurisprudenciaRelacionada casoId={1} estadoAnalisis="completado" resultado={{ updated_at: 'hoy' }} />)
  expect(await screen.findByText('AS/100/2024')).toBeTruthy()
  expect(screen.getByText('El Tribunal examinó la prueba del robo.')).toBeTruthy()
  expect(screen.getByRole('link', { name: 'Consultar fuente TSJ' }).getAttribute('href')).toContain('/100')
  expect(screen.getByRole('status').textContent).toContain('La fuente cambió')
})

it('distingue una colección vacía de un caso sin coincidencias', async () => {
  casosApi.jurisprudencia.mockResolvedValue({ data: { estado: 'sin_corpus', resultados: [] } })
  render(<JurisprudenciaRelacionada casoId={1} estadoAnalisis="completado" resultado={{ updated_at: 'hoy' }} />)
  expect(await screen.findByText(/Todavía no hay resoluciones/)).toBeTruthy()
  expect(screen.queryByText(/No se encontraron resoluciones/)).toBeNull()
})

it('refresca la jurisprudencia al completarse un nuevo análisis', async () => {
  const { rerender } = render(<JurisprudenciaRelacionada casoId={1} estadoAnalisis="procesando" resultado={{ updated_at: 'ayer' }} />)
  expect(casosApi.jurisprudencia).not.toHaveBeenCalled()
  casosApi.jurisprudencia.mockResolvedValue({ data: { estado: 'sin_coincidencias', resultados: [] } })
  rerender(<JurisprudenciaRelacionada casoId={1} estadoAnalisis="completado" resultado={{ updated_at: 'hoy' }} />)
  await waitFor(() => expect(casosApi.jurisprudencia).toHaveBeenCalledTimes(1))
  expect(await screen.findByText(/No se encontraron resoluciones/)).toBeTruthy()
})

it('expone el fallo de consulta sin presentar un ranking vacío como éxito', async () => {
  casosApi.jurisprudencia.mockRejectedValue(new Error('red'))
  render(<JurisprudenciaRelacionada casoId={1} estadoAnalisis="completado" resultado={{ updated_at: 'hoy' }} />)
  expect((await screen.findByRole('alert')).textContent).toContain('No se pudo cargar')
})
