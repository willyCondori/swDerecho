import { useState } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import AvisosVigencia from './AvisosVigencia'

const mocks = vi.hoisted(() => ({ admin: true, cambio: vi.fn(), revisar: vi.fn() }))
vi.mock('../../../auth/store/authStore', () => ({ default: (selector) => selector({ isAdmin: () => mocks.admin }) }))
vi.mock('../../../../api/normativaApi', () => ({ default: { cambio: mocks.cambio, revisarCambio: mocks.revisar } }))
vi.mock('../../../../api/catalogoApi', () => ({ default: { normas: vi.fn().mockResolvedValue({ data: [{ id: 5, nombre: 'Código Penal' }] }) } }))
const aviso = { id: 12, operacion: 'deroga', estado: 'pendiente', destino_catalogo: { encontrado: true },
  disposicion_fuente: 'disposición derogatoria única', cita: 'Se deroga el Parágrafo III del artículo 323 Bis.', mensaje: 'Afectación detectada.' }
const cambio = { id: 12, operacion: 'deroga', estado_revision: 'pendiente', norma_causante: 'LEY 1636', fecha_norma_causante: '2025-09-10',
  referencia: { norma: 'Código Penal', unidad: '323 BIS', alcance: 'Parágrafo III', parte_afectada: { tipo: 'parcial', descripcion: 'Parágrafo III', localizado: true,
    partes: [{ fragmento: 'III. Texto que se deroga.' }] } }, destino_catalogo: { encontrado: true, norma_id: 5 }, aviso, cita: aviso.cita }
function Resultado({ inicial = aviso, permitirRevision = true }) {
  const [avisos, setAvisos] = useState([inicial])
  return <AvisosVigencia avisos={avisos} permitirRevision={permitirRevision} onActualizado={(a) => setAvisos([a])} />
}
beforeEach(() => {
  vi.clearAllMocks(); mocks.admin = true
  mocks.cambio.mockResolvedValue({ data: cambio })
})
afterEach(cleanup)
it('confirma solo la parte identificada y actualiza el aviso después de la respuesta del servidor', async () => {
  mocks.revisar.mockResolvedValue({ data: { ...cambio, estado_revision: 'confirmado', aviso: { ...aviso, estado: 'confirmado', mensaje: 'Derogación parcial confirmada.', parte_afectada: cambio.referencia.parte_afectada } } })
  render(<Resultado />)
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  fireEvent.click(screen.getByRole('button', { name: 'Revisar y confirmar derogación' }))
  const confirmar = await screen.findByRole('button', { name: 'Confirmar derogación' })
  expect(confirmar.disabled).toBe(false)
  expect(screen.queryByLabelText('Fundamento de la revisión')).toBeNull()
  expect(screen.getByText('III. Texto que se deroga.')).toBeTruthy()
  fireEvent.click(confirmar)
  await waitFor(() => expect(mocks.revisar).toHaveBeenCalledWith(12, {
    descartar: false, fecha_efecto: '2025-09-10', fecha_norma_causante: '2025-09-10', norma_afectada_id: 5
  }))
  fireEvent.click(await screen.findByRole('button', { name: 'Ver todos' }))
  expect(screen.getByText('Derogación parcial confirmada')).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Revisar y confirmar derogación' })).toBeNull()
})
it.each([
  ['sin permisos', false, true, aviso],
  ['antes de guardar', true, false, aviso],
  ['destino ausente', true, true, { ...aviso, destino_catalogo: { encontrado: false } }],
  ['ya confirmado', true, true, { ...aviso, estado: 'confirmado' }],
])('no ofrece confirmación %s', (_, admin, permitirRevision, inicial) => {
  mocks.admin = admin
  render(<Resultado inicial={inicial} permitirRevision={permitirRevision} />)
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  expect(screen.queryByRole('button', { name: /Revisar y confirmar/ })).toBeNull()
})
it('conserva pendiente el aviso si el backend rechaza la revisión', async () => {
  mocks.revisar.mockRejectedValue({ response: { data: { detail: 'La norma causante debe ser posterior.' } } })
  render(<Resultado />)
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  fireEvent.click(screen.getByRole('button', { name: 'Revisar y confirmar derogación' }))
  const confirmar = await screen.findByRole('button', { name: 'Confirmar derogación' })
  fireEvent.click(confirmar)
  expect((await screen.findByRole('alert')).textContent).toContain('debe ser posterior')
  expect(screen.getByText('Revisión pendiente')).toBeTruthy()
})
it('permite revisar una abrogación y no vuelve a confirmar un efecto revisado en otra sesión', async () => {
  mocks.cambio.mockResolvedValue({ data: { ...cambio, operacion: 'abroga', estado_revision: 'confirmado', aviso: { ...aviso, operacion: 'abroga', estado: 'confirmado' } } })
  render(<Resultado inicial={{ ...aviso, operacion: 'abroga' }} />)
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  fireEvent.click(screen.getByRole('button', { name: 'Revisar y confirmar abrogación' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Ver todos' })).toBeTruthy())
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  expect(screen.getByText('Abrogación confirmada')).toBeTruthy()
  expect(mocks.revisar).not.toHaveBeenCalled()
})

it('envía la confirmación de abrogación del destino y muestra el resultado', async () => {
  const inicial = { ...aviso, operacion: 'abroga' }
  const abrogacion = { ...cambio, operacion: 'abroga', referencia: { norma: 'Ley anterior', unidad: '', alcance: 'total' }, aviso: inicial }
  mocks.cambio.mockResolvedValue({ data: abrogacion })
  mocks.revisar.mockResolvedValue({ data: { ...abrogacion, estado_revision: 'confirmado', aviso: { ...inicial, estado: 'confirmado' } } })
  render(<Resultado inicial={inicial} />)
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  fireEvent.click(screen.getByRole('button', { name: 'Revisar y confirmar abrogación' }))
  const confirmar = await screen.findByRole('button', { name: 'Confirmar abrogación' })
  fireEvent.click(confirmar)
  await waitFor(() => expect(mocks.revisar).toHaveBeenCalledWith(12, expect.objectContaining({ descartar: false, norma_afectada_id: 5 })))
  fireEvent.click(await screen.findByRole('button', { name: 'Ver todos' }))
  expect(screen.getByText('Abrogación confirmada')).toBeTruthy()
})
it('permite descartar la detección sin aplicar el efecto al catálogo', async () => {
  mocks.revisar.mockResolvedValue({ data: { ...cambio, estado_revision: 'descartado', aviso: { ...aviso, estado: 'descartado' } } })
  render(<Resultado />)
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  fireEvent.click(screen.getByRole('button', { name: 'Revisar y confirmar derogación' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Descartar detección' }))
  await waitFor(() => expect(mocks.revisar).toHaveBeenCalledWith(12, { descartar: true }))
  fireEvent.click(await screen.findByRole('button', { name: 'Ver todos' }))
  expect(screen.getByText('Detección descartada')).toBeTruthy()
})
