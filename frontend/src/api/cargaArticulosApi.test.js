import { expect, it, vi } from 'vitest'
import api from './axiosInstance'
import cargaArticulosApi from './cargaArticulosApi'

vi.mock('./axiosInstance', () => ({ default: { post: vi.fn().mockResolvedValue({ data: {} }) } }))

it('la confirmación transmite el modo, la revisión y la selección como JSON', async () => {
  await cargaArticulosApi.cargar({ archivo: new File(['pdf'], 'norma.pdf'), normaId: 7, ramaId: 2,
    modoActualizacion: 'articulos', revisionToken: 'revision-1', articulosSeleccionados: ['1', '13 bis'] })
  const [url, fd] = api.post.mock.calls.at(-1)
  expect(url).toBe('/api/catalogo/cargar-articulos/')
  expect(fd.get('modo_actualizacion')).toBe('articulos')
  expect(fd.get('revision_token')).toBe('revision-1')
  expect(JSON.parse(fd.get('articulos_seleccionados'))).toEqual(['1', '13 bis'])
})
