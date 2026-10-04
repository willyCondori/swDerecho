import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import useAuthStore from '../../auth/store/authStore'
import cargaArticulosApi from '../../../api/cargaArticulosApi'
import { useRevisionPdf } from './useRevisionPdf'
vi.mock('../../../api/cargaArticulosApi', () => ({ default: { revisarConIA: vi.fn(), revisar: vi.fn() } }))
let usuario = 0
beforeEach(() => { vi.clearAllMocks(); useAuthStore.setState({ user: { id: ++usuario } }) })
afterEach(cleanup)

it('retoma revisión, progreso y PDF al salir y entrar sin iniciar otra lectura', async () => {
  let terminar, progreso
  cargaArticulosApi.revisarConIA.mockImplementation((payload, vigente, avance) => {
    progreso = avance
    return new Promise((resolve) => { terminar = resolve })
  })
  const archivo = new File(['pdf'], 'ley.pdf')
  const primera = renderHook(() => useRevisionPdf())
  let promesa
  act(() => { promesa = primera.result.current.revisarPdf({ archivo, motorLectura: 'qwen' }) })
  primera.unmount()
  act(() => { progreso({ paso: 'Analizando disposiciones' }) })
  const segunda = renderHook(() => useRevisionPdf())
  expect(segunda.result.current.revisando).toBe(true)
  expect(segunda.result.current.pasoRevision).toBe('Analizando disposiciones')
  await act(async () => {
    await segunda.result.current.revisarPdf({ archivo, motorLectura: 'qwen' })
    terminar({ data: { articulos: [], revision_token: 'token' } })
    await promesa
  })
  expect(cargaArticulosApi.revisarConIA).toHaveBeenCalledTimes(1)
  expect(segunda.result.current.revision.payload.archivo).toBe(archivo)
  expect(segunda.result.current.revisando).toBe(false)
})

it('conserva el resultado de una revisión que terminó fuera de la pantalla', async () => {
  cargaArticulosApi.revisar.mockResolvedValue({ data: { articulos: [], revision_token: 'token' } })
  const primera = renderHook(() => useRevisionPdf())
  await act(async () => { await primera.result.current.revisarPdf({ archivo: new File(['pdf'], 'ley.pdf'), motorLectura: 'clasico' }) })
  primera.unmount()
  const segunda = renderHook(() => useRevisionPdf())
  expect(segunda.result.current.revision.revision_token).toBe('token')
  act(() => { segunda.result.current.limpiarRevision() })
  expect(segunda.result.current.revision).toBeNull()
})

it('no entrega archivos ni resultados a otra sesión de usuario', async () => {
  let terminar
  cargaArticulosApi.revisar.mockImplementation(() => new Promise((resolve) => { terminar = resolve }))
  const primera = renderHook(() => useRevisionPdf())
  let promesa
  act(() => { promesa = primera.result.current.revisarPdf({ archivo: new File(['pdf'], 'privado.pdf') }) })
  primera.unmount()
  act(() => { useAuthStore.setState({ user: { id: ++usuario } }) })
  const segunda = renderHook(() => useRevisionPdf())
  await act(async () => { terminar({ data: { articulos: [] } }); await promesa })
  expect(segunda.result.current.revision).toBeNull()
  expect(segunda.result.current.revisando).toBe(false)
})
