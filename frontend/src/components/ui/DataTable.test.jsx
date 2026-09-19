import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import DataTable from './DataTable'

afterEach(cleanup)

const FILAS = [
  { id: 1, nombre: 'Penal', sigla: 'P' },
  { id: 2, nombre: 'Civil', sigla: 'C' },
]

const COLUMNAS = [
  { key: 'nombre', header: 'Nombre' },
  { key: 'sigla', header: 'Sigla', render: (f) => `(${f.sigla})` },
  { key: 'acciones', ariaLabel: 'Acciones', actions: true, render: (f) => <button>Borrar {f.id}</button> },
]

const encabezados = (c) => c.querySelectorAll('thead th')
const filasCuerpo = (c) => c.querySelectorAll('tbody tr')

describe('DataTable', () => {
  it('muestra un encabezado por columna y una celda por columna en cada fila', () => {
    const { container } = render(<DataTable columns={COLUMNAS} rows={FILAS} />)
    expect(encabezados(container)).toHaveLength(3)
    expect(filasCuerpo(container)).toHaveLength(2)
    filasCuerpo(container).forEach((tr) => expect(tr.querySelectorAll('td')).toHaveLength(3))
  })

  it('sin render toma fila[key] y con render usa lo que devuelve', () => {
    render(<DataTable columns={COLUMNAS} rows={FILAS} />)
    expect(screen.getByText('Penal')).toBeTruthy()
    expect(screen.getByText('(P)')).toBeTruthy()
  })

  it('el esqueleto tiene tantas celdas como columnas y tantas filas como skeletonRows', () => {
    const { container } = render(<DataTable columns={COLUMNAS} rows={[]} loading skeletonRows={4} />)
    expect(filasCuerpo(container)).toHaveLength(4)
    filasCuerpo(container).forEach((tr) => expect(tr.querySelectorAll('td')).toHaveLength(COLUMNAS.length))
  })

  it('si cambia la cantidad de columnas, el esqueleto y los encabezados la siguen', () => {
    const sinAcciones = COLUMNAS.slice(0, 2)
    const { container } = render(<DataTable columns={sinAcciones} rows={[]} loading />)
    expect(encabezados(container)).toHaveLength(2)
    expect(filasCuerpo(container)[0].querySelectorAll('td')).toHaveLength(2)
  })

  it('el esqueleto de una columna de acciones se alinea a la derecha', () => {
    const { container } = render(<DataTable columns={COLUMNAS} rows={[]} loading />)
    const barras = filasCuerpo(container)[0].querySelectorAll('div')
    expect(barras[2].style.marginLeft).toBe('auto')
    expect(barras[0].style.marginLeft).toBe('')
  })

  it('cargando tiene prioridad sobre el error y sobre el estado vacío', () => {
    const { container } = render(
      <DataTable columns={COLUMNAS} rows={[]} loading error="Falló" empty={{ icon: 'ti-x', text: 'Vacío' }} />,
    )
    expect(container.querySelector('table')).not.toBeNull()
    expect(screen.queryByText('Falló')).toBeNull()
    expect(screen.queryByText('Vacío')).toBeNull()
  })

  it('con error muestra el mensaje y Reintentar llama a onRetry', () => {
    const onRetry = vi.fn()
    const { container } = render(<DataTable columns={COLUMNAS} rows={FILAS} error="No se pudo cargar" onRetry={onRetry} />)
    expect(container.querySelector('table')).toBeNull()
    expect(screen.getByText('No se pudo cargar')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('con error y sin onRetry no muestra el botón Reintentar', () => {
    render(<DataTable columns={COLUMNAS} rows={[]} error="Falló" />)
    expect(screen.queryByRole('button', { name: 'Reintentar' })).toBeNull()
  })

  it('sin filas muestra el estado vacío con su texto y su acción', () => {
    const { container } = render(
      <DataTable
        columns={COLUMNAS}
        rows={[]}
        empty={{ icon: 'ti-users', text: 'No hay nada', action: <button>Crear</button> }}
      />,
    )
    expect(container.querySelector('table')).toBeNull()
    expect(screen.getByText('No hay nada')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Crear' })).toBeTruthy()
    expect(container.querySelector('i').className).toContain('ti-users')
  })

  it('sin filas y sin "empty" muestra un mensaje por defecto', () => {
    render(<DataTable columns={COLUMNAS} rows={[]} />)
    expect(screen.getByText('No hay datos para mostrar.')).toBeTruthy()
  })

  it('la tabla siempre va dentro del contenedor con scroll horizontal', () => {
    const { container } = render(<DataTable columns={COLUMNAS} rows={FILAS} />)
    const tabla = container.querySelector('table')
    expect(tabla.parentElement.classList.contains('tableScroll')).toBe(true)
  })

  it('minWidth se aplica a la tabla', () => {
    const { container } = render(<DataTable columns={COLUMNAS} rows={FILAS} minWidth={900} />)
    expect(container.querySelector('table').style.minWidth).toBe('900px')
  })

  it('una columna sin texto usa ariaLabel como nombre accesible', () => {
    const { container } = render(<DataTable columns={COLUMNAS} rows={FILAS} />)
    expect(encabezados(container)[2].getAttribute('aria-label')).toBe('Acciones')
  })

  it('onRowClick se dispara al hacer clic en la fila', () => {
    const onRowClick = vi.fn()
    render(<DataTable columns={COLUMNAS} rows={FILAS} onRowClick={onRowClick} />)
    fireEvent.click(screen.getByText('Civil'))
    expect(onRowClick).toHaveBeenCalledWith(FILAS[1])
  })

  it('un clic en los botones de una columna de acciones NO dispara onRowClick', () => {
    const onRowClick = vi.fn()
    render(<DataTable columns={COLUMNAS} rows={FILAS} onRowClick={onRowClick} />)
    fireEvent.click(screen.getByRole('button', { name: 'Borrar 1' }))
    expect(onRowClick).not.toHaveBeenCalled()
  })

  it('rowKey personalizado se usa para identificar las filas', () => {
    const filas = [{ codigo: 'a', nombre: 'Uno' }, { codigo: 'b', nombre: 'Dos' }]
    const columnas = [{ key: 'nombre', header: 'Nombre' }]
    const { container } = render(<DataTable columns={columnas} rows={filas} rowKey={(f) => f.codigo} />)
    expect(filasCuerpo(container)).toHaveLength(2)
  })
})
