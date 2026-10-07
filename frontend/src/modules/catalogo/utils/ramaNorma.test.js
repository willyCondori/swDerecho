import { expect, it } from 'vitest'
import { ramaDeNorma } from './ramaNorma'
const ramas = [{ id: 1, nombre: 'Penal' }, { id: 2, nombre: 'Civil' }]
it('usa asociaciones únicas y conserva ambigüedades reales', () => {
  expect(ramaDeNorma({ ramas: [{ id: 2 }, { id: 2 }] }, ramas)).toBe('2')
  expect(ramaDeNorma({ nombre: 'Código Penal', ramas: [{ id: 1 }, { id: 2 }] }, ramas)).toBe('')
})
it('reconoce el Código Penal sin atribuir Penal a cualquier ley', () => {
  expect(ramaDeNorma({ nombre: 'Código Penal Boliviano' }, ramas)).toBe('1')
  expect(ramaDeNorma({ sigla: 'CPP' }, ramas)).toBe('1')
  expect(ramaDeNorma({ nombre: 'Ley 1333' }, ramas)).toBe('')
  expect(ramaDeNorma({ sigla: 'CP' }, [])).toBe('')
})
