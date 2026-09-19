import { describe, expect, it, vi } from 'vitest'
import { eliminarClienteConCasos, textoCasosActivos } from './eliminarCliente'

const errorApi = (data) => ({ response: { status: 400, data } })
const conCasos = (n) => errorApi({ code: 'cliente_con_casos_activos', casos_activos: n, detail: 'No se puede eliminar...' })

describe('textoCasosActivos', () => {
  it('singular y plural', () => {
    expect(textoCasosActivos(1)).toBe('1 caso activo')
    expect(textoCasosActivos(3)).toBe('3 casos activos')
  })
})

describe('eliminarClienteConCasos', () => {
  it('si el usuario cancela la primera confirmación no se llama a la API', async () => {
    const eliminar = vi.fn()
    const r = await eliminarClienteConCasos({ nombre: 'Ana Rojas', eliminar, confirmar: () => false, avisar: vi.fn() })
    expect(r).toEqual({ eliminado: false, casos: 0 })
    expect(eliminar).not.toHaveBeenCalled()
  })

  it('cliente sin casos: se elimina con una sola llamada y una sola confirmación', async () => {
    const eliminar = vi.fn().mockResolvedValue()
    const confirmar = vi.fn().mockReturnValue(true)
    const r = await eliminarClienteConCasos({ nombre: 'Ana Rojas', eliminar, confirmar, avisar: vi.fn() })
    expect(r).toEqual({ eliminado: true, casos: 0 })
    expect(eliminar).toHaveBeenCalledTimes(1)
    expect(eliminar).toHaveBeenCalledWith()
    expect(confirmar).toHaveBeenCalledTimes(1)
    expect(confirmar.mock.calls[0][0]).toContain('Ana Rojas')
    expect(confirmar.mock.calls[0][0]).toContain('Papelera')
  })

  it('con casos activos ofrece eliminarlos también y, si acepta, reintenta con eliminarCasos', async () => {
    const eliminar = vi.fn().mockRejectedValueOnce(conCasos(3)).mockResolvedValueOnce()
    const confirmar = vi.fn().mockReturnValue(true)
    const r = await eliminarClienteConCasos({ nombre: 'Ana Rojas', eliminar, confirmar, avisar: vi.fn() })

    expect(r).toEqual({ eliminado: true, casos: 3 })
    expect(eliminar).toHaveBeenNthCalledWith(1)
    expect(eliminar).toHaveBeenNthCalledWith(2, { eliminarCasos: true })
    expect(confirmar).toHaveBeenCalledTimes(2)
    const segunda = confirmar.mock.calls[1][0]
    expect(segunda).toContain('3 casos activos')
    expect(segunda).toContain('esos casos')
    expect(segunda).toContain('papelera')
  })

  it('con un solo caso el texto va en singular', async () => {
    const eliminar = vi.fn().mockRejectedValueOnce(conCasos(1)).mockResolvedValueOnce()
    const confirmar = vi.fn().mockReturnValue(true)
    await eliminarClienteConCasos({ nombre: 'Ana Rojas', eliminar, confirmar, avisar: vi.fn() })
    const segunda = confirmar.mock.calls[1][0]
    expect(segunda).toContain('1 caso activo')
    expect(segunda).toContain('ese caso')
  })

  it('si rechaza eliminar también los casos, el cliente no se elimina', async () => {
    const eliminar = vi.fn().mockRejectedValueOnce(conCasos(2))
    const confirmar = vi.fn().mockReturnValueOnce(true).mockReturnValueOnce(false)
    const r = await eliminarClienteConCasos({ nombre: 'Ana Rojas', eliminar, confirmar, avisar: vi.fn() })
    expect(r).toEqual({ eliminado: false, casos: 0 })
    expect(eliminar).toHaveBeenCalledTimes(1)
  })

  it('otro error se avisa con el detalle del servidor y no ofrece eliminar casos', async () => {
    const eliminar = vi.fn().mockRejectedValue(errorApi({ detail: 'Sin permiso.' }))
    const confirmar = vi.fn().mockReturnValue(true)
    const avisar = vi.fn()
    const r = await eliminarClienteConCasos({ nombre: 'Ana Rojas', eliminar, confirmar, avisar })
    expect(r.eliminado).toBe(false)
    expect(avisar).toHaveBeenCalledWith('Sin permiso.')
    expect(confirmar).toHaveBeenCalledTimes(1)
  })

  it('un error sin detalle usa un mensaje por defecto', async () => {
    const eliminar = vi.fn().mockRejectedValue(new Error('red'))
    const avisar = vi.fn()
    await eliminarClienteConCasos({ nombre: 'Ana Rojas', eliminar, confirmar: () => true, avisar })
    expect(avisar).toHaveBeenCalledWith('No se pudo eliminar el cliente.')
  })

  it('si falla la eliminación en cascada se avisa', async () => {
    const eliminar = vi.fn()
      .mockRejectedValueOnce(conCasos(2))
      .mockRejectedValueOnce(errorApi({ detail: 'Error al eliminar los casos.' }))
    const avisar = vi.fn()
    const r = await eliminarClienteConCasos({ nombre: 'Ana Rojas', eliminar, confirmar: () => true, avisar })
    expect(r).toEqual({ eliminado: false, casos: 0 })
    expect(avisar).toHaveBeenCalledWith('Error al eliminar los casos.')
  })
})
