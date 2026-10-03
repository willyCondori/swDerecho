import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import AvisosVigencia from './AvisosVigencia'
vi.mock('../../../../api/catalogoApi', () => ({ default: { descargarDocumentoNorma: vi.fn() } }))
afterEach(cleanup)
describe('AvisosVigencia', () => {
  it('muestra la causa, la fecha y la fuente antes de abrir el texto jurídico', () => {
    render(<AvisosVigencia avisos={[{ id: 1, estado: 'confirmado', mensaje: 'Este artículo fue derogado por Ley 2446 de fecha 19/03/2003.',
      cita: 'Queda derogada la disposición transitoria tercera.', url_fuente: 'http://www.gacetaoficialdebolivia.gob.bo/normas/verGratis_gob/10' }]} />)
    expect(screen.getByRole('note').textContent).toContain('Ley 2446')
    expect(screen.getByRole('note').textContent).toContain('19/03/2003')
    expect(screen.getByRole('link').getAttribute('href')).toContain('gacetaoficialdebolivia')
  })
  it('identifica una detección pendiente sin anunciar confirmación', () => {
    render(<AvisosVigencia avisos={[{ id: 2, estado: 'pendiente', mensaje: 'Afectación detectada, pendiente de verificación.' }]} />)
    expect(screen.getByRole('note').textContent).toContain('Revisión pendiente')
  })
})
