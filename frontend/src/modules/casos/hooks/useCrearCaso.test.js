import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import casosApi from '../../../api/casosApi'
import clientesApi from '../../../api/clientesApi'
import useCrearCaso from './useCrearCaso'

const { navigate } = vi.hoisted(() => ({ navigate: vi.fn() }))

vi.mock('react-router-dom', () => ({ useNavigate: () => navigate }))
vi.mock('../../../api/casosApi', () => ({
  default: { crear: vi.fn(), crearConCliente: vi.fn() },
}))
vi.mock('../../../api/clientesApi', () => ({ default: { crear: vi.fn() } }))

const cliente = { nombres: 'Ana', apellidos: 'Quispe', telefono: '71234567' }
const caso = {
  titulo: 'Demanda por incumplimiento',
  descripcion: 'Incumplimiento del contrato de alquiler.',
  rama_detectada_id: '3',
}

beforeEach(() => {
  vi.resetAllMocks()
  casosApi.crearConCliente.mockResolvedValue({ data: { id: 42 } })
  casosApi.crear.mockResolvedValue({ data: { id: 42 } })
  clientesApi.crear.mockResolvedValue({ data: { id: 7 } })
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterEach(() => vi.restoreAllMocks())

function montarFormulario({ existente = false, pdf = false } = {}) {
  const { result } = renderHook(() => useCrearCaso())
  act(() => {
    for (const [name, value] of Object.entries({
      ...cliente, titulo: caso.titulo, descripcion: caso.descripcion, rama_id: '3',
    })) {
      result.current.onChange({ target: { name, value } })
    }
    if (existente) {
      result.current.cambiarModoCliente('existente')
      result.current.seleccionarClienteExistente(7, 'Ana Quispe')
    }
    if (pdf) {
      result.current.cambiarModo('pdf')
      result.current.onChange({ target: { name: 'descripcion', value: '' } })
      result.current.onArchivoChange(new File(['%PDF-1.4'], 'caso.pdf', { type: 'application/pdf' }))
    }
  })
  return result
}

async function enviar(result) {
  await act(async () => {
    await result.current.onSubmit({ preventDefault: vi.fn() })
  })
}

describe('crear caso con cliente nuevo', () => {
  it('guarda cliente y caso en una sola petición, incluyendo el teléfono', async () => {
    const result = montarFormulario()
    await enviar(result)

    expect(casosApi.crearConCliente).toHaveBeenCalledExactlyOnceWith({ ...cliente, ...caso }, {})
    expect(clientesApi.crear).not.toHaveBeenCalled()
    expect(casosApi.crear).not.toHaveBeenCalled()
    expect(navigate).toHaveBeenCalledWith('/casos/42')
  })

  it('un rechazo del caso no crea un cliente por separado y permite reintentar', async () => {
    casosApi.crearConCliente.mockRejectedValueOnce({
      response: { data: { titulo: ['El título no es válido.'] } },
    })
    const result = montarFormulario()
    await enviar(result)

    expect(clientesApi.crear).not.toHaveBeenCalled()
    expect(navigate).not.toHaveBeenCalled()
    expect(result.current.fieldErrors.titulo).toEqual(['El título no es válido.'])
    expect(result.current.clienteForm).toEqual(cliente)
    expect(result.current.enviando).toBe(false)

    await enviar(result)
    expect(casosApi.crearConCliente).toHaveBeenCalledTimes(2)
    expect(navigate).toHaveBeenCalledWith('/casos/42')
  })

  it('envía también el PDF y los datos del cliente en la misma petición', async () => {
    const result = montarFormulario({ pdf: true })
    await enviar(result)

    const [data, config] = casosApi.crearConCliente.mock.calls[0]
    expect(data).toBeInstanceOf(FormData)
    for (const [name, value] of Object.entries({ ...cliente, ...caso, descripcion: '' })) {
      expect(data.get(name)).toBe(value)
    }
    expect(data.get('archivo_pdf').name).toBe('caso.pdf')
    expect(data.has('cliente_id')).toBe(false)
    expect(config.headers['Content-Type']).toBe('multipart/form-data')
    expect(clientesApi.crear).not.toHaveBeenCalled()
  })

  it.each(['archivo', 'archivo_pdf'])('muestra el error %s del PDF y el de la rama en sus campos', async (campo) => {
    casosApi.crearConCliente.mockRejectedValue({ response: { data: {
      [campo]: ['El archivo no es un PDF válido.'],
      rama_detectada_id: ['La rama seleccionada no existe.'],
    } } })
    const result = montarFormulario({ pdf: true })
    await enviar(result)

    expect(result.current.fieldErrors.archivo).toEqual(['El archivo no es un PDF válido.'])
    expect(result.current.fieldErrors.rama_id).toEqual(['La rama seleccionada no existe.'])
    expect(navigate).not.toHaveBeenCalled()
  })

  it('muestra un error general si falla la petición', async () => {
    casosApi.crearConCliente.mockRejectedValue(new Error('Sin conexión'))
    const result = montarFormulario()
    await enviar(result)
    expect(result.current.error).toBe('No se pudo crear el caso.')
    expect(result.current.enviando).toBe(false)
    expect(clientesApi.crear).not.toHaveBeenCalled()
  })

  it('muestra los errores generales de validación del servidor', async () => {
    casosApi.crearConCliente.mockRejectedValue({
      response: { data: { non_field_errors: ['No se pudo guardar el caso.'] } },
    })
    const result = montarFormulario()
    await enviar(result)
    expect(result.current.error).toBe('No se pudo guardar el caso.')
  })
})

describe('crear caso con cliente existente', () => {
  it.each([false, true])('con PDF=%s conserva la creación por cliente_id', async (pdf) => {
    const result = montarFormulario({ existente: true, pdf })
    await enviar(result)

    expect(casosApi.crear).toHaveBeenCalledTimes(1)
    expect(casosApi.crearConCliente).not.toHaveBeenCalled()
    expect(clientesApi.crear).not.toHaveBeenCalled()
    const [data] = casosApi.crear.mock.calls[0]
    if (pdf) {
      expect(data.get('cliente_id')).toBe('7')
      expect(data.has('nombres')).toBe(false)
    } else {
      expect(data).toEqual({ ...caso, cliente_id: 7 })
    }
    expect(navigate).toHaveBeenCalledWith('/casos/42')
  })
})
