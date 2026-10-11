import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ArticulosSeleccionados from './ArticulosSeleccionados'

const articulo = (id, valoracion) => ({ id, valoracion, articulo: {
  numero_articulo: String(id), norma_sigla: 'CP', contenido: `Contenido jurídico ${id}`,
} })
const props = { puedeEscribir: true, bloqueado: false, valorando: null, valorarArticulo: vi.fn() }
afterEach(cleanup)

describe('Artículos seleccionados', () => {
  it('muestra los principales antes que los complementarios en ambos bloques sin cambiar los datos', () => {
    const datos = [
      { ...articulo(334, 'util'), es_sugerencia: true }, articulo(331, 'util'), articulo(332, 'util'),
      { ...articulo(8, 'sin_valorar'), es_sugerencia: true }, articulo(9, 'sin_valorar'),
    ]
    render(<ArticulosSeleccionados {...props} articulos={datos} />)
    const seleccionados = within(screen.getByRole('list', { name: 'Artículos seleccionados' })).getAllByRole('combobox')
    expect(seleccionados.map((e) => e.getAttribute('aria-label'))).toEqual([
      'Utilidad del artículo 331 de CP', 'Utilidad del artículo 332 de CP', 'Utilidad del artículo 334 de CP',
    ])
    const pendientes = within(screen.getByRole('list', { name: 'Artículos sin valorar' })).getAllByRole('combobox')
    expect(pendientes.map((e) => e.getAttribute('aria-label'))).toEqual([
      'Utilidad del artículo 9 de CP', 'Utilidad del artículo 8 de CP',
    ])
    expect(datos[0].id).toBe(334)
  })
  it('mantiene los avisos cerrados por defecto y permite abrir y cerrar el bloque', () => {
    const datos = { ...articulo(281, 'util'), articulo: {
      ...articulo(281, 'util').articulo,
      avisos_vigencia: [{ id: 1, nota_historica: true, mensaje: 'Nota histórica de prueba' }],
    } }
    render(<ArticulosSeleccionados {...props} articulos={[datos]} />)
    const resumen = screen.getByText('Ver avisos normativos (1)')
    const bloque = resumen.closest('details')
    expect(bloque.open).toBe(false)
    fireEvent.click(resumen)
    expect(bloque.open).toBe(true)
    fireEvent.click(resumen)
    expect(bloque.open).toBe(false)
  })
  it('mantiene útil como recomendación complementaria y muestra su motivo', () => {
    render(<ArticulosSeleccionados {...props} articulos={[{
      ...articulo(334, 'util'), es_sugerencia: true,
      motivo_recomendacion: 'El relato menciona un intento de secuestro.',
    }]} />)
    const lista = within(screen.getByRole('list', { name: 'Artículos seleccionados' }))
    expect(lista.getByText('Recomendación complementaria')).toBeTruthy()
    expect(lista.getByText('El relato menciona un intento de secuestro.')).toBeTruthy()
    expect(lista.getByRole('combobox').value).toBe('util')
  })
  it('separa útiles, pendientes y descartados en sus listas correspondientes', () => {
    render(<ArticulosSeleccionados {...props} articulos={[articulo(1, 'util'), articulo(2, 'no_util'), articulo(3, 'sin_valorar')]} />)
    const lista = screen.getByRole('list', { name: 'Artículos seleccionados' })
    expect(within(lista).getAllByRole('listitem')).toHaveLength(1)
    expect(within(lista).queryByText('Contenido jurídico 3')).toBeNull()
    const pendientes = screen.getByRole('list', { name: 'Artículos sin valorar' })
    expect(within(pendientes).getAllByRole('listitem')).toHaveLength(1)
    expect(within(pendientes).getByText('Contenido jurídico 3')).toBeTruthy()
    expect(within(lista).queryByText('Contenido jurídico 2')).toBeNull()
    expect(screen.getByText('Artículos descartados (1)')).toBeTruthy()
  })
  it('mueve el artículo entre pendientes y seleccionados al confirmar la valoración', () => {
    const { rerender } = render(<ArticulosSeleccionados {...props} articulos={[articulo(1, 'sin_valorar')]} />)
    const seleccionados = () => within(screen.getByRole('list', { name: 'Artículos seleccionados' }))
    const pendientes = () => within(screen.getByRole('list', { name: 'Artículos sin valorar' }))
    expect(pendientes().getAllByRole('listitem')).toHaveLength(1)
    expect(seleccionados().queryByRole('listitem')).toBeNull()
    rerender(<ArticulosSeleccionados {...props} articulos={[articulo(1, 'util')]} />)
    expect(seleccionados().getAllByRole('listitem')).toHaveLength(1)
    expect(pendientes().queryByRole('listitem')).toBeNull()
    rerender(<ArticulosSeleccionados {...props} articulos={[articulo(1, 'sin_valorar')]} />)
    expect(pendientes().getAllByRole('listitem')).toHaveLength(1)
    expect(seleccionados().queryByRole('listitem')).toBeNull()
  })
  it('envía No útil y retira el artículo cuando el servidor confirma la decisión', () => {
    const enviar = vi.fn()
    const { rerender } = render(<ArticulosSeleccionados {...props} valorarArticulo={enviar} articulos={[articulo(1, 'sin_valorar')]} />)
    fireEvent.change(screen.getByRole('combobox', { name: 'Utilidad del artículo 1 de CP' }), { target: { value: 'no_util' } })
    expect(enviar).toHaveBeenCalledWith(1, 'no_util')
    rerender(<ArticulosSeleccionados {...props} valorarArticulo={enviar} articulos={[articulo(1, 'no_util')]} />)
    expect(within(screen.getByRole('list', { name: 'Artículos seleccionados' })).queryByRole('listitem')).toBeNull()
    expect(screen.getByText('No quedan artículos seleccionados.')).toBeTruthy()
  })
  it('impide valorar mientras se guarda o se analiza y respeta el modo de lectura', () => {
    const { rerender } = render(<ArticulosSeleccionados {...props} bloqueado articulos={[articulo(1, 'util')]} />)
    expect(screen.getByRole('combobox').disabled).toBe(true)
    rerender(<ArticulosSeleccionados {...props} puedeEscribir={false} articulos={[articulo(1, 'util')]} />)
    expect(screen.queryByRole('combobox')).toBeNull()
  })
  it('conserva la selección anterior, muestra aviso y permite reconfirmar', () => {
    const confirmar = vi.fn()
    const anterior = { ...articulo(1, 'util'), valoracion_desactualizada: true, seleccion_historica: true }
    render(<ArticulosSeleccionados {...props} valorarArticulo={confirmar} articulos={[anterior]} />)
    expect(within(screen.getByRole('list', { name: 'Artículos seleccionados' })).getAllByRole('listitem')).toHaveLength(1)
    expect(screen.getByText('Valorado en un contexto anterior')).toBeTruthy()
    expect(screen.getByRole('status').textContent).toContain('El contexto del caso cambió')
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar utilidad para el contexto actual' }))
    expect(confirmar).toHaveBeenCalledWith(1, 'util')
  })
})
