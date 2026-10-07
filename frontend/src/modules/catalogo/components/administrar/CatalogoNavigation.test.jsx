import { useState } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import CatalogoNavigation from './CatalogoNavigation'
afterEach(cleanup)
const tabs = [
  { value: 'ramas', label: 'Ramas' }, { value: 'jerarquias', label: 'Jerarquías' },
  { value: 'normas', label: 'Normas' }, { value: 'entidades', label: 'Entidades' },
]
function Example() {
  const [value, setValue] = useState('ramas')
  return <CatalogoNavigation tabs={tabs} value={value} onChange={setValue} />
}
it('la opción seleccionada es la primera en el documento y conserva las demás opciones', () => {
  render(<Example />)
  for (const label of ['Jerarquías', 'Normas', 'Entidades', 'Ramas']) {
    fireEvent.click(screen.getByRole('button', { name: label }))
    const buttons = within(screen.getByRole('navigation')).getAllByRole('button')
    expect(buttons).toHaveLength(4)
    expect(buttons[0].textContent).toBe(label)
    expect(buttons[0].getAttribute('aria-pressed')).toBe('true')
    expect(buttons.filter(b => b.getAttribute('aria-pressed') === 'true')).toHaveLength(1)
  }
})

it('anima la rotación sin duplicar controles y conserva la selección al finalizar', () => {
  const previous = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'animate')
  const animations = []
  Object.defineProperty(HTMLElement.prototype, 'animate', { configurable: true, value: vi.fn(() => {
    const animation = { cancel: vi.fn(), onfinish: null }
    animations.push(animation)
    return animation
  }) })
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function () {
    const index = this.tagName === 'BUTTON' ? [...this.parentElement.children].indexOf(this) : 0
    return { left: index * 100, top: 0, width: this.tagName === 'BUTTON' ? 100 : 400, height: 52, right: 400 }
  })
  try {
    render(<Example />)
    fireEvent.click(screen.getByRole('button', { name: 'Normas' }))
    expect(animations).toHaveLength(4)
    expect(within(screen.getByRole('navigation')).getAllByRole('button')[0].textContent).toBe('Normas')
    expect(screen.getByRole('navigation').getAttribute('aria-busy')).toBe('true')
    fireEvent.click(screen.getByRole('button', { name: 'Entidades' }))
    expect(animations).toHaveLength(4)
    act(() => animations[0].onfinish())
    expect(screen.getByRole('navigation').getAttribute('aria-busy')).toBe('false')
    expect(screen.getByRole('button', { name: 'Normas' }).getAttribute('aria-pressed')).toBe('true')
  } finally {
    cleanup()
    vi.restoreAllMocks()
    if (previous) Object.defineProperty(HTMLElement.prototype, 'animate', previous)
    else delete HTMLElement.prototype.animate
  }
})
