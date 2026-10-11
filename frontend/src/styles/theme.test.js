import { readFileSync } from 'node:fs'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { applyTheme, initialTheme, THEME_KEY } from './theme'

const css = (name) => readFileSync(new URL(name, import.meta.url), 'utf8')
const tokens = (text) => Object.fromEntries([...text.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]))
const night = tokens(css('./theme-night.css'))
const day = { ...night, ...tokens(css('./theme-day.css')) }
function color(palette, name) {
  const value = palette[name]
  if (value?.startsWith('var(')) return color(palette, value.match(/--[\w-]+/)[0])
  expect(value, name).toMatch(/^#[\da-f]{6}$/i)
  return value
}
function luminance(hex) {
  const rgb = hex.slice(1).match(/../g).map((x) => parseInt(x, 16) / 255)
    .map((x) => x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4)
  return rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722
}
function contrast(a, b) {
  const l = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (l[0] + 0.05) / (l[1] + 0.05)
}
beforeEach(() => { localStorage.clear(); delete document.documentElement.dataset.theme })
describe.each([['día', day], ['noche', night]])('Contraste del tema de %s', (_, palette) => {
  for (const text of ['--c-text-primary', '--c-text-secondary', '--c-text-muted']) {
    it(`${text} mantiene al menos 4,5:1 en las superficies de lectura`, () => {
      for (const bg of ['--c-bg-deep', '--c-bg-base', '--c-bg-surface', '--c-bg-elevated', '--c-bg-hover']) {
        expect(contrast(color(palette, text), color(palette, bg)), `${text} sobre ${bg}`).toBeGreaterThanOrEqual(4.5)
      }
    })
  }
  it('mantiene contraste en botones principales y selección', () => {
    for (const [fg, bg] of [['--c-on-accent', '--c-purple-600'], ['--c-on-accent', '--c-purple-700'], ['--c-selection-text', '--c-selection-bg']]) {
      expect(contrast(color(palette, fg), color(palette, bg))).toBeGreaterThanOrEqual(4.5)
    }
  })
})
it('recupera la preferencia y cambia los controles nativos mediante data-theme', () => {
  expect(initialTheme()).toBe('dark')
  expect(applyTheme('light')).toBe('light')
  expect(document.documentElement.dataset.theme).toBe('light')
  expect(localStorage.getItem(THEME_KEY)).toBe('light')
  expect(initialTheme()).toBe('light')
  applyTheme('dark', false)
  expect(localStorage.getItem(THEME_KEY)).toBe('light')
})
it('funciona si el navegador impide guardar preferencias', () => {
  const guardar = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Bloqueado') })
  expect(() => applyTheme('light')).not.toThrow()
  expect(document.documentElement.dataset.theme).toBe('light')
  guardar.mockRestore()
})
