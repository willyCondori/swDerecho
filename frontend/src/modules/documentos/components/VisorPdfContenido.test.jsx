import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import VisorPdfContenido from './VisorPdfContenido'
import catalogoApi from '../../../api/catalogoApi'
import documentosApi from '../../../api/documentosApi'

vi.mock('../../../api/catalogoApi', () => ({ default: { descargarDocumentoNorma: vi.fn() } }))
vi.mock('../../../api/documentosApi', () => ({ default: { descargar: vi.fn() } }))
vi.mock('react-pdf', async () => {
  const { useEffect } = await import('react')
  return {
    pdfjs: { GlobalWorkerOptions: {} },
    Document: ({ children, onLoadSuccess, onLoadError }) => {
      // El mock simula una única carga del documento, no cada render del padre.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      useEffect(() => { onLoadSuccess({ numPages: 3 }) }, [])
      return <div>{children}<button onClick={onLoadError}>Simular PDF dañado</button></div>
    },
    Page: ({ pageNumber, width }) => <div data-testid="pagina" data-width={width}>Contenido página {pageNumber}</div>,
  }
})
beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} })
  URL.createObjectURL = vi.fn(() => 'blob:pdf-prueba')
  URL.revokeObjectURL = vi.fn()
  catalogoApi.descargarDocumentoNorma.mockResolvedValue({ data: new Blob(['PDF']) })
  documentosApi.descargar.mockResolvedValue({ data: new Blob(['PDF']) })
})
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('abre una norma con autenticación, cambia páginas y zoom y libera el archivo al cerrar', async () => {
  const onClose = vi.fn()
  const { unmount } = render(<VisorPdfContenido documentoId={7} nombre="ley.pdf" onClose={onClose} />)
  await screen.findByText('Contenido página 1')
  expect(catalogoApi.descargarDocumentoNorma).toHaveBeenCalledWith(7, expect.any(AbortSignal))
  expect(screen.getByRole('button', { name: 'Página anterior' }).disabled).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: 'Página siguiente' }))
  expect(screen.getByText('Página 2 de 3')).toBeTruthy()
  const ancho = Number(screen.getByTestId('pagina').dataset.width)
  fireEvent.change(screen.getByLabelText('Zoom'), { target: { value: '2' } })
  expect(Number(screen.getByTestId('pagina').dataset.width)).toBe(ancho * 2)
  fireEvent.click(screen.getByRole('button', { name: 'Página siguiente' }))
  expect(screen.getByRole('button', { name: 'Página siguiente' }).disabled).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: 'Cerrar ventana' }))
  expect(onClose).toHaveBeenCalled()
  unmount()
  expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:pdf-prueba')
})

it('usa el endpoint de casos para un documento del caso', async () => {
  render(<VisorPdfContenido documentoId={8} nombre="caso.pdf" origen="caso" onClose={vi.fn()} />)
  await screen.findByText('Contenido página 1')
  expect(documentosApi.descargar).toHaveBeenCalledWith(8, expect.any(AbortSignal))
  expect(catalogoApi.descargarDocumentoNorma).not.toHaveBeenCalled()
})

it.each([[403, 'No tienes permiso para ver este documento.'], [404, 'El archivo ya no está disponible.']])('muestra el error %s sin abrir contenido', async (status, mensaje) => {
  catalogoApi.descargarDocumentoNorma.mockRejectedValue({ response: { status } })
  render(<VisorPdfContenido documentoId={7} nombre="ley.pdf" onClose={vi.fn()} />)
  expect((await screen.findByRole('alert')).textContent).toBe(mensaje)
  expect(URL.createObjectURL).not.toHaveBeenCalled()
})

it('cancela la petición al cerrar y no crea una URL para una respuesta tardía', async () => {
  let resolver
  catalogoApi.descargarDocumentoNorma.mockReturnValue(new Promise((resolve) => { resolver = resolve }))
  const { unmount } = render(<VisorPdfContenido documentoId={7} nombre="ley.pdf" onClose={vi.fn()} />)
  const signal = catalogoApi.descargarDocumentoNorma.mock.calls[0][1]
  unmount()
  expect(signal.aborted).toBe(true)
  resolver({ data: new Blob(['PDF']) })
  await waitFor(() => expect(URL.createObjectURL).not.toHaveBeenCalled())
})

it('informa cuando el PDF no se puede interpretar', async () => {
  render(<VisorPdfContenido documentoId={7} nombre="ley.pdf" onClose={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: 'Simular PDF dañado' }))
  expect(screen.getByRole('alert').textContent).toContain('No se pudo leer el PDF')
})
