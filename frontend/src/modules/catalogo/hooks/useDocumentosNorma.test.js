import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import useDocumentosNorma from './useDocumentosNorma'
import catalogoApi from '../../../api/catalogoApi'
import { descargarBlob } from '../../documentos/utils/descargas'

vi.mock('../../../api/catalogoApi', () => ({
  default: {
    documentosPorNorma: vi.fn(),
    descargarDocumentoNorma: vi.fn(),
    eliminarDocumentoNorma: vi.fn(),
  },
}))
// Evita depender de window.URL.createObjectURL (no implementado en jsdom)
// y del DOM real: acá solo interesa que el hook llame a descargarBlob
// con los datos correctos.
vi.mock('../../documentos/utils/descargas', () => ({
  descargarBlob: vi.fn(),
}))

const DOC_1 = { id: 1, nombre_original: 'ley-1.pdf', tamano: 1000, created_at: '2026-01-01T00:00:00Z' }
const DOC_2 = { id: 2, nombre_original: 'ley-2.pdf', tamano: 2000, created_at: '2026-01-02T00:00:00Z' }

beforeEach(() => {
  vi.clearAllMocks()
})
afterEach(() => {
  vi.restoreAllMocks()
})

describe('useDocumentosNorma', () => {
  it('carga los documentos de la norma al montar', async () => {
    catalogoApi.documentosPorNorma.mockResolvedValue({ data: [DOC_1, DOC_2] })

    const { result } = renderHook(() => useDocumentosNorma(7))
    expect(result.current.loading).toBe(true)

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(catalogoApi.documentosPorNorma).toHaveBeenCalledWith(7)
    expect(result.current.documentos).toEqual([DOC_1, DOC_2])
    expect(result.current.error).toBeNull()
  })

  it('no consulta nada si no hay normaId todavía', () => {
    renderHook(() => useDocumentosNorma(undefined))
    expect(catalogoApi.documentosPorNorma).not.toHaveBeenCalled()
  })

  it('un error al cargar deja un mensaje y la lista vacía', async () => {
    catalogoApi.documentosPorNorma.mockRejectedValue(new Error('caído'))

    const { result } = renderHook(() => useDocumentosNorma(7))
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.documentos).toEqual([])
    expect(result.current.error).toBe('No se pudieron cargar los documentos de esta norma.')
  })

  it('descargarDocumento pide el blob y dispara la descarga con el nombre original', async () => {
    catalogoApi.documentosPorNorma.mockResolvedValue({ data: [DOC_1] })
    const blobFalso = new Blob(['contenido'])
    catalogoApi.descargarDocumentoNorma.mockResolvedValue({ data: blobFalso })

    const { result } = renderHook(() => useDocumentosNorma(7))
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.descargarDocumento(DOC_1)
    })

    expect(catalogoApi.descargarDocumentoNorma).toHaveBeenCalledWith(1)
    expect(descargarBlob).toHaveBeenCalledWith(blobFalso, 'ley-1.pdf')
    expect(result.current.descargandoId).toBeNull()
  })

  it('eliminarDocumento saca el documento de la lista al tener éxito', async () => {
    catalogoApi.documentosPorNorma.mockResolvedValue({ data: [DOC_1, DOC_2] })
    catalogoApi.eliminarDocumentoNorma.mockResolvedValue({})

    const { result } = renderHook(() => useDocumentosNorma(7))
    await waitFor(() => expect(result.current.loading).toBe(false))

    let respuesta
    await act(async () => {
      respuesta = await result.current.eliminarDocumento(1)
    })

    expect(respuesta).toEqual({ ok: true })
    expect(catalogoApi.eliminarDocumentoNorma).toHaveBeenCalledWith(1)
    expect(result.current.documentos).toEqual([DOC_2])
  })

  it('eliminarDocumento deja el mensaje del backend si falla (p. ej. sin permiso)', async () => {
    catalogoApi.documentosPorNorma.mockResolvedValue({ data: [DOC_1] })
    catalogoApi.eliminarDocumentoNorma.mockRejectedValue({
      response: { data: { detail: 'No tiene permiso para realizar esta acción.' } },
    })

    const { result } = renderHook(() => useDocumentosNorma(7))
    await waitFor(() => expect(result.current.loading).toBe(false))

    let respuesta
    await act(async () => {
      respuesta = await result.current.eliminarDocumento(1)
    })

    expect(respuesta).toEqual({ ok: false, error: 'No tiene permiso para realizar esta acción.' })
    // No se borra optimísticamente de la lista si el backend lo rechazó.
    expect(result.current.documentos).toEqual([DOC_1])
    expect(result.current.error).toBe('No tiene permiso para realizar esta acción.')
  })
})
