import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import useCasoDetail from './useCasoDetail'
import casosApi from '../../../api/casosApi'

vi.mock('../../../api/casosApi', () => ({
  default: {
    obtener: vi.fn(),
    seguimiento: vi.fn(),
    articulos: vi.fn(),
    subirPdf: vi.fn(),
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
