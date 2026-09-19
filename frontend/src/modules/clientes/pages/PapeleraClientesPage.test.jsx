import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import PapeleraClientesPage, { textoCasos, textoEliminacion } from './PapeleraClientesPage'
import clientesApi from '../../../api/clientesApi'

vi.mock('../../../api/clientesApi', () => ({
  default: { papelera: vi.fn(), restaurar: vi.fn() },
}))

const CON_CASOS = {
  id: 1, nombre_completo: 'Ana Rojas', telefono: '71234567',
  eliminado_at: '2026-09-18T14:30:00Z', eliminado_por_nombre: 'Laura Quispe',
  casos_para_restaurar: 2, created_at: '2026-01-01T00:00:00Z',
}
const SIN_CASOS = {
  id: 2, nombre_completo: 'Luis Mamani', telefono: null,
  eliminado_at: null, eliminado_por_nombre: null,
  casos_para_restaurar: 0, created_at: '2026-01-02T00:00:00Z',
}

const montar = () => render(<MemoryRouter><PapeleraClientesPage /></MemoryRouter>)

beforeEach(() => {
  vi.clearAllMocks()
  clientesApi.papelera.mockResolvedValue({ data: { count: 2, results: [CON_CASOS, SIN_CASOS] } })
})
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('textos', () => {
  it('textoCasos usa singular y plural', () => {
    expect(textoCasos(1)).toBe('1 caso')
    expect(textoCasos(2)).toBe('2 casos')
  })

  it('textoEliminacion cubre con y sin fecha/usuario', () => {
    expect(textoEliminacion(CON_CASOS)).toContain('por Laura Quispe')
    expect(textoEliminacion({ ...CON_CASOS, eliminado_por_nombre: null })).not.toContain(' por ')
    expect(textoEliminacion(SIN_CASOS)).toContain('fecha desconocida')
  })
})

describe('PapeleraClientesPage', () => {
  it('lista los clientes eliminados con quién los eliminó y cuántos casos volverán', async () => {
    montar()
    expect(await screen.findByText('Ana Rojas')).toBeTruthy()
    expect(screen.getByText('Luis Mamani')).toBeTruthy()
    expect(screen.getByText(/por Laura Quispe/)).toBeTruthy()
    expect(screen.getByText('2 casos')).toBeTruthy()
    expect(screen.getByText('2 clientes eliminados')).toBeTruthy()
  })

  it('papelera vacía muestra el estado vacío', async () => {
    clientesApi.papelera.mockResolvedValue({ data: { count: 0, results: [] } })
    montar()
    expect(await screen.findByText('La papelera está vacía.')).toBeTruthy()
  })

  it('un error de carga muestra el mensaje y permite reintentar', async () => {
    clientesApi.papelera.mockRejectedValueOnce(new Error('caído'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    montar()
    expect(await screen.findByText('No se pudo cargar la papelera de clientes.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByText('Ana Rojas')).toBeTruthy()
  })

  it('restaurar avisa cuántos casos vuelven, restaura y confirma el resultado', async () => {
    const confirmar = vi.spyOn(window, 'confirm').mockReturnValue(true)
    clientesApi.restaurar.mockResolvedValue({ data: { id: 1, casos_restaurados: 2 } })
    montar()
    await screen.findByText('Ana Rojas')

    fireEvent.click(screen.getAllByRole('button', { name: /Restaurar/ })[0])

    expect(confirmar.mock.calls[0][0]).toContain('Ana Rojas')
    expect(confirmar.mock.calls[0][0]).toContain('sus 2 casos eliminados con él')
    await waitFor(() => expect(clientesApi.restaurar).toHaveBeenCalledWith(1))
    expect(await screen.findByText('Ana Rojas fue restaurado, junto con 2 casos.')).toBeTruthy()
    expect(clientesApi.papelera).toHaveBeenCalledTimes(2) // recarga la lista
  })

  it('restaurar un cliente sin casos no menciona casos', async () => {
    const confirmar = vi.spyOn(window, 'confirm').mockReturnValue(true)
    clientesApi.restaurar.mockResolvedValue({ data: { id: 2, casos_restaurados: 0 } })
    montar()
    await screen.findByText('Luis Mamani')
    fireEvent.click(screen.getAllByRole('button', { name: /Restaurar/ })[1])
    expect(confirmar.mock.calls[0][0]).not.toContain('casos')
    expect(await screen.findByText('Luis Mamani fue restaurado.')).toBeTruthy()
  })

  it('si el usuario cancela la confirmación no se restaura nada', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    montar()
    await screen.findByText('Ana Rojas')
    fireEvent.click(screen.getAllByRole('button', { name: /Restaurar/ })[0])
    expect(clientesApi.restaurar).not.toHaveBeenCalled()
  })

  it('si el servidor rechaza la restauración muestra el mensaje', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.spyOn(console, 'error').mockImplementation(() => {})
    clientesApi.restaurar.mockRejectedValue({ response: { data: { detail: 'No se pudo restaurar por un conflicto.' } } })
    montar()
    await screen.findByText('Ana Rojas')
    fireEvent.click(screen.getAllByRole('button', { name: /Restaurar/ })[0])
    expect(await screen.findByText('No se pudo restaurar por un conflicto.')).toBeTruthy()
  })

  it('la búsqueda se envía al servidor solo con 2 o más caracteres', async () => {
    montar()
    await screen.findByText('Ana Rojas')
    const caja = screen.getByPlaceholderText('Buscar por nombre o apellido...')

    fireEvent.change(caja, { target: { value: 'a' } })
    await waitFor(() => expect(clientesApi.papelera).toHaveBeenCalledTimes(2))
    expect(clientesApi.papelera.mock.calls[1][0].search).toBeUndefined()

    fireEvent.change(caja, { target: { value: 'ana' } })
    await waitFor(() => expect(clientesApi.papelera.mock.calls.at(-1)[0].search).toBe('ana'))
  })
})
