import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent } from '@testing-library/react'
import AvisosVigencia from './AvisosVigencia'
vi.mock('../../../../api/catalogoApi', () => ({ default: { descargarDocumentoNorma: vi.fn() } }))
afterEach(cleanup)
describe('AvisosVigencia', () => {
  it('muestra la causa, la fecha y la fuente antes de abrir el texto jurídico', () => {
    render(<AvisosVigencia avisos={[{ id: 1, estado: 'confirmado', mensaje: 'Este artículo fue derogado por Ley 2446 de fecha 19/03/2003.',
      cita: 'Queda derogada la disposición transitoria tercera.', url_fuente: 'http://www.gacetaoficialdebolivia.gob.bo/normas/verGratis_gob/10' }]} />)
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
    expect(screen.getByRole('note').textContent).toContain('Ley 2446')
    expect(screen.getByRole('note').textContent).toContain('19/03/2003')
    expect(screen.getByRole('link').getAttribute('href')).toContain('gacetaoficialdebolivia')
  })
  it('identifica una detección pendiente sin anunciar confirmación', () => {
    render(<AvisosVigencia avisos={[{ id: 2, estado: 'pendiente', mensaje: 'Afectación detectada, pendiente de verificación.' }]} />)
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
    expect(screen.getByRole('note').textContent).toContain('Revisión pendiente')
  })
})

it('un plazo es informativo y no se presenta como derogación pendiente', () => {
  render(<AvisosVigencia avisos={[{ id: 3, operacion: 'temporal', estado: 'pendiente', norma_causante: 'Ley 1636', mensaje: 'Afectación parcial del artículo o disposición : temporal', parte_afectada: { tipo: 'parcial' } }]} />)
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  expect(screen.getByRole('note').textContent).toContain('Aviso informativo')
  expect(screen.getByRole('note').textContent).not.toContain('Afectación parcial')
  expect(screen.getByRole('note').textContent).not.toContain('Revisión pendiente')
})

it('explica qué hacer si el artículo exacto no está cargado', () => {
  render(<AvisosVigencia avisos={[{ id: 4, operacion: 'deroga', estado: 'pendiente', mensaje: 'Artículo 281 Quater', destino_catalogo: { encontrado: false } }]} />)
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  expect(screen.getByRole('note').textContent).toContain('Solo aviso')
  expect(screen.getByRole('note').textContent).toContain('primero incorpore esa norma o artículo')
})

it('conserva el motivo específico de una referencia judicial o histórica', () => {
  render(<AvisosVigencia avisos={[{ id: 5, operacion: 'general', estado: 'pendiente', mensaje: 'Referencia judicial: revisar sentencia y aclaraciones.', cita: 'SC 0034/2006' }]} />)
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  expect(screen.getByRole('note').textContent).toContain('Referencia judicial')
  expect(screen.getByRole('note').textContent).not.toContain('Cláusula general')
})

it('presenta incorporaciones históricas como nota de la versión, sin pedir aplicar otra reforma', () => {
  render(<AvisosVigencia avisos={[{ id: 6, nota_historica: true, operacion: 'incorpora', estado: 'pendiente', mensaje: 'Nota histórica: incorporado por Ley 700.', parte_afectada: { tipo: 'parcial', descripcion: 'Numeral 1' } }]} />)
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  expect(screen.getByRole('note').textContent).toContain('Nota histórica de la versión del PDF')
  expect(screen.getByRole('note').textContent).not.toContain('Revisión pendiente')
  expect(screen.getByRole('note').textContent).not.toContain('Numeral 1')
})

it('oculta inicialmente, muestra grupos de diez y filtra sin mezclar históricos y derogaciones', () => {
  const avisos = Array.from({ length: 23 }, (_, i) => ({ id: i, operacion: i < 12 ? 'deroga' : 'incorpora', nota_historica: i >= 12, estado: 'pendiente', mensaje: `Aviso ${i}` }))
  render(<AvisosVigencia avisos={avisos} />)
  expect(screen.queryAllByRole('note')).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: 'Ver más' }))
  expect(screen.getAllByRole('note')).toHaveLength(10)
  fireEvent.click(screen.getByRole('button', { name: 'Ver más' }))
  expect(screen.getAllByRole('note')).toHaveLength(20)
  fireEvent.change(screen.getByLabelText('Tipo de aviso'), { target: { value: 'historico' } })
  expect(screen.queryAllByRole('note')).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  expect(screen.getAllByRole('note')).toHaveLength(11)
  fireEvent.click(screen.getByRole('button', { name: 'Ocultar' }))
  expect(screen.queryAllByRole('note')).toHaveLength(0)
  fireEvent.change(screen.getByLabelText('Tipo de aviso'), { target: { value: 'deroga' } })
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  expect(screen.getAllByRole('note')).toHaveLength(12)
})
it('diferencia confirmados, pendientes, judiciales y fuentes incompletas', () => {
  render(<AvisosVigencia avisos={[
    { id: 1, operacion: 'deroga', estado: 'pendiente', mensaje: 'Artículo pendiente' },
    { id: 2, operacion: 'abroga', estado: 'confirmado', mensaje: 'Norma confirmada' },
    { id: 3, operacion: 'general', estado: 'pendiente', mensaje: 'Referencia judicial: revisar sentencia' },
    { id: 4, nota_historica: true, operacion: 'modifica', mensaje: 'Fecha: por verificar', requiere_verificacion_fuente: true },
  ]} />)
  fireEvent.change(screen.getByLabelText('Estado del aviso'), { target: { value: 'pendiente' } })
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  expect(screen.getAllByRole('note')).toHaveLength(1)
  expect(screen.getByRole('note').textContent).toContain('Artículo pendiente')
  fireEvent.change(screen.getByLabelText('Estado del aviso'), { target: { value: 'confirmado' } })
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  expect(screen.getByRole('note').textContent).toContain('Norma confirmada')
  fireEvent.change(screen.getByLabelText('Estado del aviso'), { target: { value: 'fuente' } })
  fireEvent.click(screen.getByRole('button', { name: 'Ver todos' }))
  expect(screen.getByRole('note').textContent).toContain('por verificar')
})
