import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import TextoVigencia from './TextoVigencia'
afterEach(cleanup)
describe('TextoVigencia', () => {
  it('resalta solo el parágrafo derogado confirmado y conserva el resto', () => {
    const { container } = render(<TextoVigencia texto={'I. Vigente. II. Derogado. III. Vigente.'} avisos={[{
      operacion: 'deroga', estado: 'confirmado', parte_afectada: { tipo: 'parcial', partes: [{ descripcion: 'Parágrafo II', fragmento: 'II. Derogado.' }] },
    }]} />)
    expect(screen.getByLabelText('Parte derogada: Parágrafo II').textContent).toBe('II. Derogado.')
    expect(container.textContent).toContain('I. Vigente.')
    expect(container.textContent).toContain('III. Vigente.')
  })
  it('no resalta como derogado un fragmento pendiente de verificación', () => {
    const { container } = render(<TextoVigencia texto="Texto afectado" avisos={[{ operacion: 'deroga', estado: 'pendiente',
      parte_afectada: { tipo: 'parcial', partes: [{ descripcion: 'Parágrafo II', fragmento: 'Texto afectado' }] } }]} />)
    expect(container.querySelector('mark')).toBeNull()
  })
})
