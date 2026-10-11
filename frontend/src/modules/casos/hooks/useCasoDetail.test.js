import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import useCasoDetail from './useCasoDetail'
import casosApi from '../../../api/casosApi'

vi.mock('../../../api/casosApi', () => ({
  default: {
    obtener: vi.fn(),
    estadoAnalisis: vi.fn(),
    seguimiento: vi.fn(),
    articulos: vi.fn(),
    subirPdf: vi.fn(),
    valorarArticulo: vi.fn(),
  },
}))

const CASO = { id: 1, codigo: 'CASO-0001', resultado: null }

// Simula el 400 que devuelve el backend cuando validar_pdf() rechaza el
// archivo (firma inválida o PDF corrupto), tal como llega a subirPdf.
const errorArchivo = (mensaje) => ({ response: { status: 400, data: { archivo_pdf: [mensaje] } } })

beforeEach(() => {
  vi.clearAllMocks()
  casosApi.obtener.mockResolvedValue({ data: CASO })
  casosApi.seguimiento.mockResolvedValue({ data: [] })
  vi.spyOn(console, 'error').mockImplementation(() => {})
})
afterEach(() => {
  vi.restoreAllMocks()
})

async function montarCargado() {
  const { result } = renderHook(() => useCasoDetail(1))
  await waitFor(() => expect(result.current.loading).toBe(false))
  return result
}

it('guarda la utilidad y conserva la selección anterior si falla la petición', async () => {
  casosApi.obtener.mockResolvedValue({ data: { ...CASO, resultado: {} } })
  casosApi.articulos.mockResolvedValue({ data: [{ id: 7, valoracion: 'sin_valorar' }] })
  casosApi.valorarArticulo.mockResolvedValue({ data: { resultado_id: 7, valoracion: 'util' } })
  const result = await montarCargado()
  await act(async () => { await result.current.valorarArticulo(7, 'util') })
  expect(casosApi.valorarArticulo).toHaveBeenCalledWith(1, { resultado_id: 7, valor: 'util' })
  expect(result.current.articulos[0].valoracion).toBe('util')
  casosApi.valorarArticulo.mockRejectedValue(new Error('Sin conexión'))
  await act(async () => { await result.current.valorarArticulo(7, 'no_util') })
  expect(result.current.articulos[0].valoracion).toBe('util')
  expect(result.current.errorValoracion).toBe('No se pudo guardar la valoración.')
})

it('envía No útil y conserva la decisión confirmada por el servidor', async () => {
  casosApi.obtener.mockResolvedValue({ data: { ...CASO, resultado: {} } })
  casosApi.articulos.mockResolvedValue({ data: [{ id: 7, valoracion: 'sin_valorar' }] })
  casosApi.valorarArticulo.mockResolvedValue({ data: { resultado_id: 7, valoracion: 'no_util' } })
  const result = await montarCargado()
  await act(async () => { expect(await result.current.valorarArticulo(7, 'no_util')).toBe(true) })
  expect(casosApi.valorarArticulo).toHaveBeenCalledWith(1, { resultado_id: 7, valor: 'no_util' })
  expect(result.current.articulos[0].valoracion).toBe('no_util')
})

it('carga selecciones históricas sin ranking y envía su referencia al confirmar', async () => {
  casosApi.articulos.mockResolvedValue({ data: [{ id: 'valoracion-9', valoracion_id: 9,
    seleccion_historica: true, valoracion: 'util', valoracion_desactualizada: true }] })
  casosApi.valorarArticulo.mockResolvedValue({ data: { valoracion: 'util', valoracion_id: 10, valoracion_desactualizada: false } })
  const result = await montarCargado()
  expect(result.current.articulos).toHaveLength(1)
  await act(async () => { await result.current.valorarArticulo('valoracion-9', 'util') })
  expect(casosApi.valorarArticulo).toHaveBeenCalledWith(1, { valoracion_id: 9, valor: 'util' })
  expect(result.current.articulos[0].valoracion_desactualizada).toBe(false)
  expect(result.current.articulos[0].valoracion_id).toBe(10)
})

describe('useCasoDetail.subirPdf — validación de contenido del PDF', () => {
  it('un archivo con firma inválida muestra el mensaje del backend, no uno genérico', async () => {
    casosApi.subirPdf.mockRejectedValue(
      errorArchivo('El archivo no es un PDF válido (no tiene la firma esperada).')
    )
    const result = await montarCargado()

    let ok
    await act(async () => {
      ok = await result.current.subirPdf(new File(['no es un pdf'], 'x.pdf'))
    })

    expect(ok).toBe(false)
    expect(result.current.error).toBe('El archivo no es un PDF válido (no tiene la firma esperada).')
    expect(result.current.subiendoPdf).toBe(false)
    // Un intento rechazado no debe volver a pedir el caso (nada que refrescar)
    expect(casosApi.obtener).toHaveBeenCalledTimes(1)
  })

  it('un PDF corrupto muestra ese otro mensaje del backend', async () => {
    casosApi.subirPdf.mockRejectedValue(
      errorArchivo('El archivo está dañado o no se pudo leer como PDF.')
    )
    const result = await montarCargado()

    await act(async () => {
      await result.current.subirPdf(new File(['%PDF-1.4 roto'], 'x.pdf'))
    })

    expect(result.current.error).toBe('El archivo está dañado o no se pudo leer como PDF.')
  })

  it('sin mensaje específico del backend cae al mensaje genérico', async () => {
    casosApi.subirPdf.mockRejectedValue(new Error('red'))
    const result = await montarCargado()

    await act(async () => {
      await result.current.subirPdf(new File(['x'], 'x.pdf'))
    })

    expect(result.current.error).toBe('No se pudo adjuntar el PDF.')
  })

  it('un PDF válido se adjunta, limpia el error previo y recarga el caso', async () => {
    casosApi.subirPdf
      .mockRejectedValueOnce(errorArchivo('El archivo no es un PDF válido (no tiene la firma esperada).'))
      .mockResolvedValueOnce({ data: { detail: 'PDF adjuntado correctamente.' } })
    const result = await montarCargado()

    await act(async () => {
      await result.current.subirPdf(new File(['x'], 'x.pdf'))
    })
    expect(result.current.error).toBeTruthy()

    casosApi.obtener.mockResolvedValue({ data: { ...CASO, resultado: null } })
    await act(async () => {
      const ok = await result.current.subirPdf(new File(['%PDF-1.4 real'], 'x.pdf'))
      expect(ok).toBe(true)
    })

    expect(result.current.error).toBeNull()
    expect(casosApi.obtener).toHaveBeenCalledTimes(2) // recarga tras el éxito
  })
})


it('consulta progreso ligero y refresca el detalle cuando termina', async () => {
  const uuid = '9347d919-57dd-49a1-bcc5-dfa8553913b8'
  casosApi.obtener.mockResolvedValueOnce({ data: { ...CASO, id: uuid, estado_analisis: 'procesando' } })
    .mockResolvedValue({ data: { ...CASO, id: uuid, estado_analisis: 'completado', resultado: {} } })
  casosApi.articulos.mockResolvedValue({ data: [] })
  casosApi.estadoAnalisis.mockResolvedValue({ data: { id: uuid, estado_analisis: 'completado' } })
  vi.useFakeTimers()
  const { result, unmount } = renderHook(() => useCasoDetail(uuid))
  await act(async () => {})
  expect(result.current.loading).toBe(false)
  try {
    await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
    expect(casosApi.estadoAnalisis).toHaveBeenCalledWith(uuid)
    expect(casosApi.obtener).toHaveBeenCalledTimes(2)
    expect(result.current.caso.estado_analisis).toBe('completado')
    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    expect(casosApi.estadoAnalisis).toHaveBeenCalledTimes(1)
  } finally { unmount(); vi.useRealTimers() }
})

it('no solapa consultas de progreso cuando la respuesta tarda', async () => {
  casosApi.obtener.mockResolvedValue({ data: { ...CASO, estado_analisis: 'procesando' } })
  casosApi.articulos.mockResolvedValue({ data: [] })
  let completar
  casosApi.estadoAnalisis.mockReturnValue(new Promise(resolve => { completar = resolve }))
  vi.useFakeTimers()
  const { result, unmount } = renderHook(() => useCasoDetail(1))
  await act(async () => {})
  expect(result.current.loading).toBe(false)
  try {
    await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
    expect(casosApi.estadoAnalisis).toHaveBeenCalledTimes(1)
    await act(async () => { completar({ data: { estado_analisis: 'error' } }) })
  } finally { unmount(); vi.useRealTimers() }
})
