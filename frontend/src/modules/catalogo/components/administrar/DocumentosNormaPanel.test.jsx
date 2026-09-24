import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'

import DocumentosNormaPanel from './DocumentosNormaPanel'
import catalogoApi from '../../../../api/catalogoApi'

vi.mock('../../../../api/catalogoApi', () => ({
  default: {
    documentosPorNorma: vi.fn(),
    descargarDocumentoNorma: vi.fn(),
    eliminarDocumentoNorma: vi.fn(),
  },
}))
vi.mock('../../../documentos/utils/descargas', () => ({
  descargarBlob: vi.fn(),
  formatTamano: (bytes) => `${bytes}B`,
}))

let esAdmin = true
vi.mock('../../../auth/store/authStore', () => ({
  default: (selector) => selector({ isAdmin: () => esAdmin }),
}))

const NORMA = { id: 7, nombre: 'Código de prueba' }
const DOC = {
  id: 1, nombre_original: 'ley.pdf', tamano: 1024,
  rama_nombre: 'Penal', subido_por_nombre: 'Ana', created_at: '2026-01-01T00:00:00Z',
}

beforeEach(() => {
  vi.clearAllMocks()
  esAdmin = true
  window.confirm = vi.fn(() => true)
})
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

const montar = (props = {}) => render(<DocumentosNormaPanel norma={NORMA} onClose={vi.fn()} {...props} />)

describe('DocumentosNormaPanel', () => {
  it('muestra el estado vacío cuando la norma no tiene documentos', async () => {
    catalogoApi.documentosPorNorma.mockResolvedValue({ data: [] })
    montar()
    expect(await screen.findByText(/todavía no tiene ningún PDF cargado/)).toBeTruthy()
  })

  it('lista los documentos con su nombre y metadata', async () => {
    catalogoApi.documentosPorNorma.mockResolvedValue({ data: [DOC] })
    montar()
    expect(await screen.findByText('ley.pdf')).toBeTruthy()
    expect(screen.getByText(/Penal/)).toBeTruthy()
    expect(screen.getByText(/Ana/)).toBeTruthy()
  })

  it('el título muestra el nombre de la norma', async () => {
    catalogoApi.documentosPorNorma.mockResolvedValue({ data: [] })
    montar()
    expect(await screen.findByText(/Código de prueba/)).toBeTruthy()
  })

  it('llama a onClose al hacer clic en cerrar', async () => {
    catalogoApi.documentosPorNorma.mockResolvedValue({ data: [] })
    const onClose = vi.fn()
    montar({ onClose })
    await screen.findByText(/todavía no tiene ningún PDF cargado/)
    fireEvent.click(screen.getByTitle('Cerrar'))
    expect(onClose).toHaveBeenCalled()
  })

  it('un usuario sin rol admin no ve el botón de eliminar, pero sí el de descargar', async () => {
    esAdmin = false
    catalogoApi.documentosPorNorma.mockResolvedValue({ data: [DOC] })
    montar()
    await screen.findByText('ley.pdf')
    expect(screen.queryByTitle('Eliminar')).toBeNull()
    expect(screen.getByTitle('Descargar')).toBeTruthy()
  })

  it('admin puede eliminar tras confirmar, y el documento desaparece de la lista', async () => {
    catalogoApi.documentosPorNorma.mockResolvedValue({ data: [DOC] })
    catalogoApi.eliminarDocumentoNorma.mockResolvedValue({})
    montar()
    await screen.findByText('ley.pdf')

    fireEvent.click(screen.getByTitle('Eliminar'))

    expect(window.confirm).toHaveBeenCalled()
    await waitFor(() => expect(catalogoApi.eliminarDocumentoNorma).toHaveBeenCalledWith(1))
    await waitFor(() => expect(screen.queryByText('ley.pdf')).toBeNull())
  })

  it('si se cancela la confirmación, no se llama a eliminar', async () => {
    window.confirm = vi.fn(() => false)
    catalogoApi.documentosPorNorma.mockResolvedValue({ data: [DOC] })
    montar()
    await screen.findByText('ley.pdf')

    fireEvent.click(screen.getByTitle('Eliminar'))

    expect(catalogoApi.eliminarDocumentoNorma).not.toHaveBeenCalled()
    expect(screen.getByText('ley.pdf')).toBeTruthy()
  })

  it('descargar llama a la API con el id del documento', async () => {
    catalogoApi.documentosPorNorma.mockResolvedValue({ data: [DOC] })
    catalogoApi.descargarDocumentoNorma.mockResolvedValue({ data: new Blob(['x']) })
    montar()
    await screen.findByText('ley.pdf')

    fireEvent.click(screen.getByTitle('Descargar'))

    await waitFor(() => expect(catalogoApi.descargarDocumentoNorma).toHaveBeenCalledWith(1))
  })

  it('un error al cargar muestra el mensaje de error', async () => {
    catalogoApi.documentosPorNorma.mockRejectedValue(new Error('caído'))
    montar()
    expect(await screen.findByText(/No se pudieron cargar los documentos/)).toBeTruthy()
  })
})
