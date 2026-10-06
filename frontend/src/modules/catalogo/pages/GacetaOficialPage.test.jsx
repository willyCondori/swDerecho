import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import GacetaOficialPage from './GacetaOficialPage'
import useAuthStore from '../../auth/store/authStore'
import { useBorradorCarga } from '../hooks/useBorradorCarga'
import { FORM_INICIAL } from '../utils/formCargaInicial'
const mocks = vi.hoisted(() => ({ navigate: vi.fn(), limpiar: vi.fn(), archivo: null }))
vi.mock('react-router-dom', () => ({ useNavigate: () => mocks.navigate }))
vi.mock('../../../api/catalogoApi', () => ({ default: {
  ramas: vi.fn().mockResolvedValue({ data: [{ id: 2, nombre: 'Penal' }] }),
  jerarquias: vi.fn().mockResolvedValue({ data: [{ id: 1, nombre: 'Ley' }] }),
} }))
vi.mock('../hooks/useRevisionPdf', () => ({ useRevisionPdf: () => ({ revisando: false, limpiarRevision: mocks.limpiar }) }))
vi.mock('../components/articulos/GacetaPanel', () => ({ default: ({ onElegir }) =>
  <button onClick={() => onElegir({ id: 4, titulo: 'Ley 1636', tipo: 'Ley', numero: '1636',
    fecha_publicacion: '2025-09-10', url_fuente: 'https://fuente.gob.bo/1636' }, mocks.archivo)}>Revisar e incorporar</button>
}))
beforeEach(() => { vi.clearAllMocks(); useAuthStore.setState({ user: { id: 500 } }); mocks.archivo = new File(['pdf'], 'Ley-1636.pdf') })
afterEach(() => { cleanup(); useAuthStore.setState({ user: null }) })
function Destino() { const { borrador } = useBorradorCarga(FORM_INICIAL); return <output>{JSON.stringify({ nombre: borrador.form.nombreDocumento,
  rama: borrador.form.ramaId, jerarquia: borrador.form.jerarquiaId, oficial: borrador.form.documentoOficialId, archivo: borrador.archivo?.name })}</output> }
it('traslada el PDF oficial y su identidad al borrador antes de navegar al formulario', async () => {
  render(<><GacetaOficialPage /><Destino /></>)
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Revisar e incorporar' })) })
  expect(screen.getByRole('status').textContent).toBe(JSON.stringify({ nombre: 'Ley 1636', rama: 2, jerarquia: 1, oficial: 4, archivo: 'Ley-1636.pdf' }))
  expect(mocks.limpiar).toHaveBeenCalledTimes(1)
  expect(mocks.navigate).toHaveBeenCalledWith('/catalogo/cargar')
})
