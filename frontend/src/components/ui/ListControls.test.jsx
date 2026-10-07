import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import Pagination from './Pagination'
import ArticlePagination from '../../modules/catalogo/components/articulos/Pagination'
import FilterTabs from './FilterTabs'
import SearchField from './SearchField'
import RamaForm from '../../modules/catalogo/components/administrar/RamaForm'
import EntidadForm from '../../modules/catalogo/components/administrar/EntidadForm'
import RolForm from '../../modules/usuarios/components/RolForm'
import RamaTable from '../../modules/catalogo/components/administrar/RamaTable'
import DisposicionesList from '../../modules/catalogo/components/articulos/DisposicionesList'

afterEach(cleanup)

describe('shared list controls', () => {
  it('numbered navigation preserves boundaries, range and current page', () => {
    const onPageChange = vi.fn()
    const { rerender } = render(<Pagination page={1} totalPages={7} count={67} pageSize={10} onPageChange={onPageChange} />)
    expect(screen.getByText('Mostrando 1–10 de 67 registros')).toBeTruthy()
    expect(screen.getByLabelText('Página anterior').disabled).toBe(true)
    expect(screen.getByRole('button', { name: '1' }).getAttribute('aria-current')).toBe('page')
    fireEvent.click(screen.getByLabelText('Última página'))
    expect(onPageChange).toHaveBeenCalledWith(7)
    rerender(<Pagination page={7} totalPages={7} count={67} pageSize={10} onPageChange={onPageChange} />)
    expect(screen.getByText('Mostrando 61–67 de 67 registros')).toBeTruthy()
    expect(screen.getByLabelText('Página siguiente').disabled).toBe(true)
    fireEvent.click(screen.getByLabelText('Página anterior'))
    expect(onPageChange).toHaveBeenLastCalledWith(6)
  })

  it('compact pages navigate without a record count and disappear on a single page', () => {
    const onPageChange = vi.fn()
    const { rerender } = render(<Pagination variant="simple" page={2} totalPages={3} onPageChange={onPageChange} />)
    expect(screen.getAllByRole('button')).toHaveLength(2)
    fireEvent.click(screen.getByLabelText('Página siguiente'))
    expect(onPageChange).toHaveBeenCalledWith(3)
    rerender(<Pagination variant="simple" page={1} totalPages={1} onPageChange={onPageChange} />)
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('article page size remains available when there are no results', () => {
    const onPageSizeChange = vi.fn()
    render(<ArticlePagination page={1} totalPages={0} totalCount={0} firstItem={0} lastItem={0}
      pageSize={10} visiblePages={[]} onPageChange={vi.fn()} onPageSizeChange={onPageSizeChange} />)
    expect(screen.getByText('Mostrando 0–0 de 0 artículos')).toBeTruthy()
    expect(screen.getByLabelText('Página siguiente').disabled).toBe(true)
    fireEvent.change(screen.getByLabelText('Artículos por página'), { target: { value: '25' } })
    expect(onPageSizeChange).toHaveBeenCalledWith(25)
  })

  it('search and clear deliver text instead of DOM events', () => {
    const onChange = vi.fn()
    const { rerender } = render(<SearchField label="Buscar artículos" value="" onChange={onChange} clearable />)
    fireEvent.change(screen.getByLabelText('Buscar artículos'), { target: { value: '323 bis' } })
    expect(onChange).toHaveBeenCalledWith('323 bis')
    rerender(<SearchField label="Buscar artículos" value="323 bis" onChange={onChange} clearable />)
    fireEvent.click(screen.getByLabelText('Limpiar búsqueda'))
    expect(onChange).toHaveBeenLastCalledWith('')
  })

  it('filter buttons expose selection and do not submit enclosing forms', () => {
    const onChange = vi.fn(), onSubmit = vi.fn()
    render(<form onSubmit={onSubmit}><FilterTabs options={[{ value: 'activa', label: 'Activa' }, { value: 'eliminada', label: 'Eliminada' }]}
      value="activa" onChange={onChange} /></form>)
    expect(screen.getByRole('button', { name: 'Activa' }).getAttribute('aria-pressed')).toBe('true')
    fireEvent.click(screen.getByRole('button', { name: 'Eliminada' }))
    expect(onChange).toHaveBeenCalledWith('eliminada')
    expect(onSubmit).not.toHaveBeenCalled()
  })
})

describe('domain adapters', () => {
  it.each([[RamaForm, 'Crear rama'], [EntidadForm, 'Crear entidad'], [RolForm, 'Crear rol']])(
    'keeps field errors, cancel and busy state for %s', (Form, createLabel) => {
      const onCancel = vi.fn()
      const props = { form: { nombre: '', descripcion: '' }, fieldErrors: { nombre: 'Obligatorio' },
        onChange: vi.fn(), onSubmit: vi.fn(), onCancel }
      const { rerender } = render(<Form {...props} />)
      expect(screen.getByText('Obligatorio')).toBeTruthy()
      fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
      expect(onCancel).toHaveBeenCalledOnce()
      expect(screen.getByRole('button', { name: createLabel })).toBeTruthy()
      rerender(<Form {...props} enviando />)
      expect(screen.getByRole('button', { name: 'Guardando...' }).disabled).toBe(true)
      expect(screen.getByLabelText('Nombre').disabled).toBe(true)
    }
  )

  it('entity table callbacks receive the selected record and deleted rows only offer recovery', () => {
    const row = { id: 9, nombre: 'Penal', estado: true }
    const onEditar = vi.fn(), onRecuperar = vi.fn()
    const { rerender } = render(<RamaTable ramas={[row]} onEditar={onEditar} />)
    fireEvent.click(screen.getByTitle('Editar'))
    expect(onEditar).toHaveBeenCalledWith(row)
    const deleted = { ...row, estado: false }
    rerender(<RamaTable ramas={[deleted]} onRecuperar={onRecuperar} />)
    expect(screen.queryByTitle('Editar')).toBeNull()
    fireEvent.click(screen.getByTitle('Recuperar rama'))
    expect(onRecuperar).toHaveBeenCalledWith(deleted)
  })

  it('disposition table keeps source links and full text in both preview and catalog', () => {
    const rows = [{ key: 'dd-1', tipo: 'derogatoria', numero: 'ÚNICA', texto: 'Se deroga el parágrafo III.', norma: 'Ley 1636' }]
    const { container, rerender } = render(<DisposicionesList rows={rows} />)
    expect(container.querySelectorAll('th')).toHaveLength(3)
    expect(screen.getByText(rows[0].texto)).toBeTruthy()
    rerender(<DisposicionesList rows={rows} showNorma renderLinks={() => <a href="/catalogo/avisos">Consultar avisos</a>} />)
    expect(container.querySelectorAll('th')).toHaveLength(4)
    expect(screen.getByRole('link').getAttribute('href')).toBe('/catalogo/avisos')
    expect(screen.getByText('Ley 1636')).toBeTruthy()
  })
})
