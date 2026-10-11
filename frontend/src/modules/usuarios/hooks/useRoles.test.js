import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useRoles } from './useRoles'
import usuariosApi from '../../../api/usuariosApi'
vi.mock('../../../api/usuariosApi', () => ({ default: { listarRoles: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())
describe('Listado de roles para formularios', () => {
  it('presenta los roles activos devueltos por la API', async () => {
    usuariosApi.listarRoles.mockResolvedValue({ data: [{ id: 1, nombre: 'Abogado' }] })
    const { result } = renderHook(() => useRoles())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.roles).toEqual([{ id: 1, nombre: 'Abogado' }])
    expect(result.current.error).toBeNull()
  })
  it('informa un fallo sin presentar roles ficticios', async () => {
    usuariosApi.listarRoles.mockRejectedValue(new Error('Sin conexión'))
    const { result } = renderHook(() => useRoles())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.roles).toEqual([])
    expect(result.current.error).toContain('No se pudieron cargar')
  })
  it('tolera una respuesta sin roles', async () => {
    usuariosApi.listarRoles.mockResolvedValue({ data: null })
    const { result } = renderHook(() => useRoles())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.roles).toEqual([])
  })
})
