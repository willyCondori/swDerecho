import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import normativaApi from '../../../../api/normativaApi'
import CambiosNormativosPanel from './CambiosNormativosPanel'

vi.mock('../../../../api/normativaApi', () => ({ default: { cambios: vi.fn(), revisarCambio: vi.fn() } }))
vi.mock('../../../../api/catalogoApi', () => ({ default: {
  normas: vi.fn().mockResolvedValue({ data: [{ id: 10, nombre: 'Ley 11080' }] }), actualizarNorma: vi.fn(),
} }))
afterEach(() => { cleanup(); vi.clearAllMocks() })
const base = { id: 1, operacion: 'abroga', estado_revision: 'pendiente',
  norma_causante: 'Ley 2298', fuente_nombre: 'Ley 2298', fecha_norma_causante: '2001-12-20',
  disposicion_fuente: 'disposición final tercera', referencia: { norma: 'Ley 11080', unidad: '', alcance: 'total' },
  cita: 'Queda abrogada la Ley 11080.' }

it('el destino ausente tiene solo aviso y no ofrece confirmar abrogación', async () => {
  normativaApi.cambios.mockResolvedValue({ data: [{ ...base,
    destino_catalogo: { encontrado: false, mensaje: 'Solo aviso: la norma no está cargada.' } }] })
  render(<CambiosNormativosPanel />)
  expect(await screen.findByText('Solo aviso: la norma no está cargada.')).toBeTruthy()
  expect(screen.getByText(/Disposición de origen: disposición final tercera/)).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Confirmar abrogación' })).toBeNull()
  expect(normativaApi.revisarCambio).not.toHaveBeenCalled()
})

it('el destino cargado se aplica únicamente después de confirmar con fundamento', async () => {
  normativaApi.cambios.mockResolvedValue({ data: [{ ...base, norma_afectada: 10,
    destino_catalogo: { encontrado: true, norma_id: 10, mensaje: 'Destino encontrado. Requiere confirmación.' } }] })
  normativaApi.revisarCambio.mockResolvedValue({ data: {} })
  render(<CambiosNormativosPanel />)
  const boton = await screen.findByRole('button', { name: 'Confirmar abrogación' })
  expect(boton.disabled).toBe(true)
  expect(normativaApi.revisarCambio).not.toHaveBeenCalled()
  fireEvent.change(screen.getByPlaceholderText('Verificación de fecha, alcance, competencia y vigencia'),
    { target: { value: 'Fuente y alcance verificados.' } })
  expect(boton.disabled).toBe(false)
  fireEvent.click(boton)
  await waitFor(() => expect(normativaApi.revisarCambio).toHaveBeenCalledWith(1, expect.objectContaining({
    descartar: false, norma_afectada_id: 10, observacion: 'Fuente y alcance verificados.', fecha_efecto: '2001-12-20',
  })))
})
