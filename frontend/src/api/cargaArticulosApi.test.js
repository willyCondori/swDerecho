import { expect, it, vi } from 'vitest'
import api from './axiosInstance'
import cargaArticulosApi from './cargaArticulosApi'

vi.mock('./axiosInstance', () => ({ default: { post: vi.fn().mockResolvedValue({ data: {} }) } }))

it('la revisión envía el PDF como multipart y evita heredar application/json', async () => {
  const archivo = new File(['pdf'], 'norma.pdf', { type: 'application/pdf' })
  await cargaArticulosApi.revisar({ archivo, normaId: 7, ramaId: 2 })
  const [url, fd, config] = api.post.mock.calls.at(-1)
  expect(url).toBe('/api/catalogo/cargar-articulos/revisar/')
  expect(fd).toBeInstanceOf(FormData)
  expect(fd.get('archivo').name).toBe('norma.pdf')
  expect(fd.get('norma_id')).toBe('7')
  expect(fd.get('rama_id')).toBe('2')
  expect(config.headers['Content-Type']).toBe('multipart/form-data')
  expect(config.timeout).toBe(120000)
})

it('la confirmación transmite el modo, la revisión y la selección como JSON', async () => {
  await cargaArticulosApi.cargar({ archivo: new File(['pdf'], 'norma.pdf'), normaId: 7, ramaId: 2,
    modoActualizacion: 'articulos', revisionToken: 'revision-1', articulosSeleccionados: ['1', '13 bis'] })
  const [url, fd] = api.post.mock.calls.at(-1)
  expect(url).toBe('/api/catalogo/cargar-articulos/')
  expect(fd.get('modo_actualizacion')).toBe('articulos')
  expect(fd.get('revision_token')).toBe('revision-1')
  expect(JSON.parse(fd.get('articulos_seleccionados'))).toEqual(['1', '13 bis'])
})
