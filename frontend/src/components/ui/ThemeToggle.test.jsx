import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import ThemeToggle from './ThemeToggle'
import { applyTheme, initialTheme, THEME_KEY } from '../../styles/theme'

beforeEach(() => { localStorage.clear(); delete document.documentElement.dataset.theme })
afterEach(() => { cleanup(); vi.restoreAllMocks() })
describe('Tema de día y noche', () => {
  it('cambia el tema y conserva la elección al reiniciar', () => {
    applyTheme(initialTheme(), false)
    render(<ThemeToggle />)
    fireEvent.click(screen.getByRole('button', { name: 'Activar tema de día' }))
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(initialTheme()).toBe('light')
    fireEvent.click(screen.getByRole('button', { name: 'Activar tema de noche' }))
    expect(initialTheme()).toBe('dark')
  })
  it('funciona si el navegador impide guardar preferencias', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw Error('bloqueado') })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw Error('bloqueado') })
    render(<ThemeToggle />)
    fireEvent.click(screen.getByRole('button', { name: 'Activar tema de día' }))
    expect(document.documentElement.dataset.theme).toBe('light')
  })
  it('sincroniza la preferencia cambiada desde otra pestaña', () => {
    render(<ThemeToggle />)
    localStorage.setItem(THEME_KEY, 'light')
    fireEvent(window, new StorageEvent('storage', { key: THEME_KEY, newValue: 'light' }))
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(screen.getByRole('button', { name: 'Activar tema de noche' })).toBeTruthy()
  })
  it('ignora preferencias desconocidas', () => {
    localStorage.setItem(THEME_KEY, 'invalido')
    expect(initialTheme()).toBe('dark')
  })
})
