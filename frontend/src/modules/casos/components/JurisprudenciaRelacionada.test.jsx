import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import JurisprudenciaRelacionada from './JurisprudenciaRelacionada'
import casosApi from '../../../api/casosApi'
import jurisprudenciaApi from '../../../api/jurisprudenciaApi'
vi.mock('../../../api/jurisprudenciaApi', () => ({ default: { obtener: vi.fn() } }))

vi.mock('../../../api/casosApi', () => ({ default: { jurisprudencia: vi.fn(), valorarJurisprudencia: vi.fn() } }))
afterEach(() => { cleanup(); vi.clearAllMocks() })

it('abre y cierra el texto completo en el mismo caso sin navegar al catálogo', async () => {
  casosApi.jurisprudencia.mockResolvedValue({ data: { estado: 'completado', resultados: [{
    id: 1, registro_id: 9415, numero: 'AS/541/2006', score_semantico: .55,
    fragmento: 'Fragmento del caso', url_fuente: 'https://apigenesis.tsj.bo/api/v1/resoluciones/48043',
  }] } })
  jurisprudenciaApi.obtener.mockResolvedValue({ data: { numero: 'AS/541/2006', texto: 'Texto íntegro del fallo. Fragmento del caso', sala: 'Sala Penal' } })
  render(<JurisprudenciaRelacionada casoId={1} estadoAnalisis="completado" resultado={{ updated_at: 'hoy' }} />)
  fireEvent.click(await screen.findByRole('button', { name: 'Leer resolución completa' }))
  expect(await screen.findByText('Texto íntegro del fallo.')).toBeTruthy()
  expect(screen.getByRole('article', { name: 'Texto de la resolución' }).querySelector('mark').textContent).toBe('Fragmento del caso')
  expect(jurisprudenciaApi.obtener).toHaveBeenCalledWith(9415, expect.objectContaining({ signal: expect.any(AbortSignal) }))
  expect(screen.getByRole('dialog')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Cerrar ventana' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  expect(screen.getByText('Fragmento del caso')).toBeTruthy()
})

it('identifica recomendaciones de menor confianza sin presentar el puntaje como probabilidad', async () => {
  casosApi.jurisprudencia.mockResolvedValue({ data: { estado: 'completado', resultados: [{
    id: 2, numero: 'AS/541/2006', score_semantico: .547, es_sugerencia: true,
    coincidencias: ['Robo'], motivo_recomendacion: 'Coincidencia de menor confianza; revisar su pertinencia.',
    fragmento: 'El Tribunal examinó el robo agravado.', url_fuente: 'https://apigenesis.tsj.bo/api/v1/resoluciones/48043',
  }] } })
  render(<JurisprudenciaRelacionada casoId={1} estadoAnalisis="completado" resultado={{ updated_at: 'hoy' }} />)
  expect(await screen.findByText('Recomendación complementaria')).toBeTruthy()
  expect(screen.getByText('Relación identificada: Robo')).toBeTruthy()
  expect(screen.getByText('Coincidencia de menor confianza; revisar su pertinencia.')).toBeTruthy()
  expect(screen.queryByText(/Similitud semántica/)).toBeNull()
})

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
  expect(await screen.findByText(/No se encontraron fragmentos/)).toBeTruthy()
})

it('expone el fallo de consulta sin presentar un ranking vacío como éxito', async () => {
  casosApi.jurisprudencia.mockRejectedValue(new Error('red'))
  render(<JurisprudenciaRelacionada casoId={1} estadoAnalisis="completado" resultado={{ updated_at: 'hoy' }} />)
  expect((await screen.findByRole('alert')).textContent).toContain('No se pudo cargar')
})

const resolucionValorada = (id, valoracion = 'sin_valorar') => ({ id, registro_id: id, numero: `AS/${id}/2024`,
  fragmento: `Fragmento ${id}`, score_semantico: .8, valoracion, url_fuente: 'https://apigenesis.tsj.bo' })

it('separa útiles, pendientes y descartadas y conserva el aviso de contexto anterior', async () => {
  casosApi.jurisprudencia.mockResolvedValue({ data: { estado: 'completado', resultados: [
    { ...resolucionValorada(1, 'util'), valoracion_desactualizada: true },
    resolucionValorada(2), resolucionValorada(3, 'no_util'),
  ] } })
  render(<JurisprudenciaRelacionada casoId="caso" estadoAnalisis="completado" resultado={{ updated_at: 'hoy' }} puedeEscribir />)
  await screen.findByText('AS/1/2024')
  expect(within(screen.getByRole('list', { name: 'Jurisprudencia seleccionada' })).getByText('AS/1/2024')).toBeTruthy()
  expect(within(screen.getByRole('list', { name: 'Jurisprudencia sin valorar' })).getByText('AS/2/2024')).toBeTruthy()
  expect(screen.getByText('Jurisprudencia descartada (1)')).toBeTruthy()
  expect(screen.getByText('Valorada en un contexto anterior')).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Confirmar utilidad para el contexto actual' })).toBeTruthy()
})

it('envía la utilidad y mueve la resolución al bloque de seleccionadas', async () => {
  casosApi.jurisprudencia.mockResolvedValueOnce({ data: { estado: 'completado', resultados: [resolucionValorada(1)] } })
    .mockResolvedValue({ data: { estado: 'completado', resultados: [resolucionValorada(1, 'util')] } })
  casosApi.valorarJurisprudencia.mockResolvedValue({ data: { valoracion: 'util' } })
  render(<JurisprudenciaRelacionada casoId="caso" estadoAnalisis="completado" resultado={{ updated_at: 'hoy' }} puedeEscribir />)
  fireEvent.change(await screen.findByLabelText('Utilidad de la resolución AS/1/2024'), { target: { value: 'util' } })
  await waitFor(() => expect(within(screen.getByRole('list', { name: 'Jurisprudencia seleccionada' })).getByText('AS/1/2024')).toBeTruthy())
  expect(casosApi.valorarJurisprudencia).toHaveBeenCalledWith('caso', { resultado_id: 1, valor: 'util' })
})

it('confirma una selección histórica mediante su valoración y no el resultado eliminado', async () => {
  const r = { ...resolucionValorada('valoracion-juris-4', 'util'), numero: 'AS/4/2024', valoracion_id: 4,
    valoracion_desactualizada: true }
  casosApi.jurisprudencia.mockResolvedValue({ data: { estado: 'completado', resultados: [r] } })
  casosApi.valorarJurisprudencia.mockResolvedValue({ data: {} })
  render(<JurisprudenciaRelacionada casoId="caso" estadoAnalisis="completado" resultado={{ updated_at: 'hoy' }} puedeEscribir />)
  fireEvent.click(await screen.findByRole('button', { name: 'Confirmar utilidad para el contexto actual' }))
  await waitFor(() => expect(casosApi.valorarJurisprudencia).toHaveBeenCalledWith('caso', { valoracion_id: 4, valor: 'util' }))
})

it('informa un rechazo y conserva la resolución sin cambiar su valoración', async () => {
  casosApi.jurisprudencia.mockResolvedValue({ data: { estado: 'completado', resultados: [resolucionValorada(1)] } })
  casosApi.valorarJurisprudencia.mockRejectedValue({ response: { data: { detail: 'Vuelve a analizar el caso.' } } })
  render(<JurisprudenciaRelacionada casoId="caso" estadoAnalisis="completado" resultado={{ updated_at: 'hoy' }} puedeEscribir />)
  fireEvent.change(await screen.findByLabelText('Utilidad de la resolución AS/1/2024'), { target: { value: 'util' } })
  expect((await screen.findByRole('alert')).textContent).toBe('Vuelve a analizar el caso.')
  expect(screen.getByLabelText('Utilidad de la resolución AS/1/2024').value).toBe('sin_valorar')
})

it('los lectores ven los bloques pero no los controles de valoración', async () => {
  casosApi.jurisprudencia.mockResolvedValue({ data: { estado: 'completado', resultados: [resolucionValorada(1)] } })
  render(<JurisprudenciaRelacionada casoId="caso" estadoAnalisis="completado" resultado={{ updated_at: 'hoy' }} />)
  await screen.findByText('AS/1/2024')
  expect(screen.queryByLabelText(/Utilidad de la resolución/)).toBeNull()
})
