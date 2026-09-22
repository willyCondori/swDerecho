import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useCargaArticulos } from './useCargaArticulos'
import cargaArticulosApi from '../../../api/cargaArticulosApi'
import catalogoApi from '../../../api/catalogoApi'

vi.mock('../../../api/cargaArticulosApi', () => ({
  default: { activas: vi.fn(), estado: vi.fn(), cargar: vi.fn() },
}))
vi.mock('../../../api/catalogoApi', () => ({
  default: { jerarquias: vi.fn(), ramas: vi.fn() },
}))

// Simula el 400 que devuelve el backend cuando el archivo no pasa
// validar_pdf(): firma inválida o PDF corrupto.
const errorArchivo = (mensaje) => ({ response: { status: 400, data: { archivo: [mensaje] } } })

beforeEach(() => {
  vi.clearAllMocks()
  catalogoApi.jerarquias.mockResolvedValue({ data: [] })
  catalogoApi.ramas.mockResolvedValue({ data: [] })
  cargaArticulosApi.activas.mockResolvedValue({ data: [] })
})
afterEach(() => {
  vi.restoreAllMocks()
})

describe('useCargaArticulos — validación de contenido del PDF', () => {
  it('un archivo con la firma de PDF inválida muestra el mensaje del backend, sin quedar "procesando"', async () => {
    cargaArticulosApi.cargar.mockRejectedValue(
      errorArchivo('El archivo no es un PDF válido (no tiene la firma esperada).')
    )
    const { result } = renderHook(() => useCargaArticulos())
    await waitFor(() => expect(result.current.loadingOpts).toBe(false))

    let respuesta
    await act(async () => {
      respuesta = await result.current.cargar({ archivo: new File(['no es un pdf'], 'x.pdf') })
    })

    expect(respuesta).toEqual({
      success: false,
      error: 'El archivo no es un PDF válido (no tiene la firma esperada).',
      fieldErrors: { archivo: ['El archivo no es un PDF válido (no tiene la firma esperada).'] },
    })
    expect(result.current.error).toBe('El archivo no es un PDF válido (no tiene la firma esperada).')
    expect(result.current.procesando).toBe(false)
    expect(result.current.enviando).toBe(false)
    expect(result.current.taskId).toBeNull()
    // No debe haber arrancado el seguimiento de una carga que nunca se aceptó
    expect(cargaArticulosApi.estado).not.toHaveBeenCalled()
  })

  it('un PDF corrupto (pasa la firma pero pypdf no puede abrirlo) muestra ese otro mensaje', async () => {
    cargaArticulosApi.cargar.mockRejectedValue(
      errorArchivo('El archivo está dañado o no se pudo leer como PDF.')
    )
    const { result } = renderHook(() => useCargaArticulos())
    await waitFor(() => expect(result.current.loadingOpts).toBe(false))

    await act(async () => {
      await result.current.cargar({ archivo: new File(['%PDF-1.4 roto'], 'x.pdf') })
    })

    expect(result.current.error).toBe('El archivo está dañado o no se pudo leer como PDF.')
  })

  it('un intento fallido no deja rastros para el siguiente intento con un PDF válido', async () => {
    cargaArticulosApi.cargar
      .mockRejectedValueOnce(errorArchivo('El archivo no es un PDF válido (no tiene la firma esperada).'))
      .mockResolvedValueOnce({ data: { task_id: 'task-1' } })
    cargaArticulosApi.estado.mockResolvedValue({ data: { estado: 'STARTED', progreso: 10, paso: 'Procesando...' } })

    const { result } = renderHook(() => useCargaArticulos())
    await waitFor(() => expect(result.current.loadingOpts).toBe(false))

    await act(async () => {
      await result.current.cargar({ archivo: new File(['x'], 'x.pdf') })
    })
    expect(result.current.error).toBeTruthy()

    await act(async () => {
      const r = await result.current.cargar({ archivo: new File(['%PDF-1.4 real'], 'x.pdf') })
      expect(r.success).toBe(true)
    })

    expect(result.current.error).toBeNull()
    expect(result.current.taskId).toBe('task-1')
    expect(result.current.procesando).toBe(true)
  })
})
