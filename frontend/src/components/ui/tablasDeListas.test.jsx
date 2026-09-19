/**
 * Las tablas de las pantallas de administración se construyen con DataTable.
 * Estas pruebas comprueban, para cada una, que el esqueleto de carga tiene la
 * misma cantidad de celdas que encabezados (el error que tenía UsuarioTable
 * antes: 5 celdas de esqueleto para 4 columnas) y que van dentro del
 * contenedor con scroll horizontal.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import UsuarioTable from '../../modules/usuarios/components/UsuarioTable'
import RolTable from '../../modules/usuarios/components/RolTable'
import RamaTable from '../../modules/catalogo/components/administrar/RamaTable'
import JerarquiaTable from '../../modules/catalogo/components/administrar/JerarquiaTable'
import EntidadTable from '../../modules/catalogo/components/administrar/EntidadTable'
import NormaTable from '../../modules/catalogo/components/administrar/NormaTable'

afterEach(cleanup)

const noop = () => {}
const acciones = { onRetry: noop, onEditar: noop, onEliminar: noop, onRecuperar: noop, onCrearPrimero: noop, onVer: noop }

const TABLAS = [
  ['UsuarioTable', UsuarioTable, 'usuarios', 4],
  ['RolTable', RolTable, 'roles', 4],
  ['RamaTable', RamaTable, 'ramas', 4],
  ['JerarquiaTable', JerarquiaTable, 'jerarquias', 4],
  ['EntidadTable', EntidadTable, 'entidades', 4],
  ['NormaTable', NormaTable, 'normas', 5],
]

describe.each(TABLAS)('%s', (_nombre, Tabla, prop, columnasEsperadas) => {
  it('el esqueleto de carga tiene tantas celdas como encabezados', () => {
    const { container } = render(<Tabla {...{ [prop]: [] }} loading error={null} {...acciones} />)
    const encabezados = container.querySelectorAll('thead th')
    expect(encabezados).toHaveLength(columnasEsperadas)
    const filas = container.querySelectorAll('tbody tr')
    expect(filas.length).toBeGreaterThan(0)
    filas.forEach((tr) => expect(tr.querySelectorAll('td')).toHaveLength(columnasEsperadas))
  })

  it('la tabla va dentro del contenedor con scroll horizontal', () => {
    const { container } = render(<Tabla {...{ [prop]: [] }} loading error={null} {...acciones} />)
    expect(container.querySelector('table').parentElement.classList.contains('tableScroll')).toBe(true)
  })

  it('con error muestra el mensaje y permite reintentar', () => {
    const onRetry = vi.fn()
    render(<Tabla {...{ [prop]: [] }} loading={false} error="Sin conexión" {...acciones} onRetry={onRetry} />)
    expect(screen.getByText('Sin conexión')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})

describe('UsuarioTable', () => {
  const usuario = { id: 7, usuario: 'laura', estado: true, rol: { nombre: 'Abogado' }, perfil: { nombres: 'Laura', apellidos: 'Quispe', telefono: '70000000' } }

  it('clic en la fila abre el usuario, pero los botones de acción no', () => {
    const onVer = vi.fn()
    const onEditar = vi.fn()
    render(<UsuarioTable usuarios={[usuario]} loading={false} error={null} {...acciones} onVer={onVer} onEditar={onEditar} />)
    fireEvent.click(screen.getByText('Laura Quispe'))
    expect(onVer).toHaveBeenCalledWith(7)
    onVer.mockClear()
    fireEvent.click(screen.getByTitle('Editar'))
    expect(onEditar).toHaveBeenCalledWith(7)
    expect(onVer).not.toHaveBeenCalled()
  })

  it('un usuario eliminado solo ofrece Recuperar', () => {
    render(<UsuarioTable usuarios={[{ ...usuario, estado: false }]} loading={false} error={null} {...acciones} />)
    expect(screen.getByTitle('Recuperar usuario')).toBeTruthy()
    expect(screen.queryByTitle('Editar')).toBeNull()
    expect(screen.queryByTitle('Eliminar')).toBeNull()
  })
})

describe('RolTable', () => {
  it('el rol Administrador no se puede eliminar', () => {
    const roles = [{ id: 1, nombre: 'Administrador', descripcion: '', estado: true }, { id: 2, nombre: 'Abogado', descripcion: 'x', estado: true }]
    render(<RolTable roles={roles} loading={false} error={null} {...acciones} />)
    const [eliminarAdmin, eliminarAbogado] = screen.getAllByRole('button').filter((b) => b.title.includes('Eliminar') || b.title.includes('no puede desactivarse'))
    expect(eliminarAdmin.disabled).toBe(true)
    expect(eliminarAbogado.disabled).toBe(false)
  })
})

describe('estados vacíos', () => {
  it('EntidadTable y NormaTable distinguen "sin resultados de búsqueda" de "no hay datos"', () => {
    const { unmount } = render(<EntidadTable entidades={[]} loading={false} error={null} busqueda="xyz" {...acciones} />)
    expect(screen.getByText(/No se encontraron entidades para “xyz”/)).toBeTruthy()
    unmount()
    render(<NormaTable normas={[]} loading={false} error={null} busqueda="" mostrandoEliminadas {...acciones} />)
    expect(screen.getByText('No hay normas eliminadas.')).toBeTruthy()
  })

  it('las tablas con acción "crear primero" la ofrecen cuando no hay datos', () => {
    const onCrearPrimero = vi.fn()
    render(<RamaTable ramas={[]} loading={false} error={null} {...acciones} onCrearPrimero={onCrearPrimero} />)
    fireEvent.click(screen.getByRole('button', { name: /Nueva rama/ }))
    expect(onCrearPrimero).toHaveBeenCalledTimes(1)
  })
})
