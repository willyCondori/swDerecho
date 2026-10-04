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

it('un plazo es informativo y no se presenta como derogación pendiente', () => {
  render(<AvisosVigencia avisos={[{ id: 3, operacion: 'temporal', estado: 'pendiente', norma_causante: 'Ley 1636', mensaje: 'Afectación parcial del artículo o disposición : temporal', parte_afectada: { tipo: 'parcial' } }]} />)
  expect(screen.getByRole('note').textContent).toContain('Aviso informativo')
  expect(screen.getByRole('note').textContent).not.toContain('Afectación parcial')
  expect(screen.getByRole('note').textContent).not.toContain('Revisión pendiente')
})

it('explica qué hacer si el artículo exacto no está cargado', () => {
  render(<AvisosVigencia avisos={[{ id: 4, operacion: 'deroga', estado: 'pendiente', mensaje: 'Artículo 281 Quater', destino_catalogo: { encontrado: false } }]} />)
  expect(screen.getByRole('note').textContent).toContain('Solo aviso')
  expect(screen.getByRole('note').textContent).toContain('primero incorpore esa norma o artículo')
})

it('conserva el motivo específico de una referencia judicial o histórica', () => {
  render(<AvisosVigencia avisos={[{ id: 5, operacion: 'general', estado: 'pendiente', mensaje: 'Referencia judicial: revisar sentencia y aclaraciones.', cita: 'SC 0034/2006' }]} />)
  expect(screen.getByRole('note').textContent).toContain('Referencia judicial')
  expect(screen.getByRole('note').textContent).not.toContain('Cláusula general')
})
