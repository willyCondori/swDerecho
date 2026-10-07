import { render, screen, cleanup } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import ResultSummary from './ResultSummary'
afterEach(cleanup)
const resumen = { norma: 'Ley 1333', rama: 'Penal', total_encontrados: 10, guardados: 10, errores: 0, duplicados: 0 }
it('muestra los nombres de las normas realmente creadas', () => {
  render(<MemoryRouter><ResultSummary resumen={{ ...resumen, normas_creadas: [{ id: 10, nombre: 'Ley 1333' }] }} /></MemoryRouter>)
  expect(screen.getByRole('status', { name: 'Normas nuevas creadas' }).textContent).toContain('Ley 1333')
})
it('distingue reutilizar una norma existente de crearla', () => {
  render(<MemoryRouter><ResultSummary resumen={{ ...resumen, normas_creadas: [], normas_reutilizadas: [{ id: 10, nombre: 'Ley 1333' }] }} /></MemoryRouter>)
  expect(screen.getByText(/Normas existentes reutilizadas: Ley 1333/)).toBeTruthy()
  expect(screen.queryByRole('status', { name: 'Normas nuevas creadas' })).toBeNull()
})
