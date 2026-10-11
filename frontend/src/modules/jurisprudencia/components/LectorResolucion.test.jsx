import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import LectorResolucion from './LectorResolucion'
import jurisprudenciaApi from '../../../api/jurisprudenciaApi'

vi.mock('../../../api/jurisprudenciaApi', () => ({ default: { obtener: vi.fn() } }))
afterEach(() => { cleanup(); vi.clearAllMocks() })
const cargar = (texto) => jurisprudenciaApi.obtener.mockResolvedValue({ data: { numero: 'AS/1/2024', texto, sala: 'Sala Penal' } })

it('resalta el fragmento del caso y permite ocultarlo y volver a él', async () => {
  cargar('Inicio. El Tribunal examinó el robo agravado. Decisión final.')
  render(<LectorResolucion id={1} fragmento="El Tribunal examinó el robo agravado." onClose={vi.fn()} />)
  const ocultar = await screen.findByRole('button', { name: 'Ocultar resaltado' })
  const texto = screen.getByRole('article', { name: 'Texto de la resolución' })
  expect(texto.querySelector('mark').textContent).toBe('El Tribunal examinó el robo agravado.')
  expect(texto.textContent.trim()).toBe('Inicio. El Tribunal examinó el robo agravado. Decisión final.')
  expect(ocultar.getAttribute('aria-pressed')).toBe('true')
  fireEvent.click(ocultar)
  expect(screen.getByRole('button', { name: 'Mostrar resaltado' }).getAttribute('aria-pressed')).toBe('false')
  fireEvent.click(screen.getByRole('button', { name: 'Ir al fragmento relacionado' }))
  expect(screen.getByRole('button', { name: 'Ocultar resaltado' }).getAttribute('aria-pressed')).toBe('true')
})

it('avisa si el fragmento anterior no se encuentra y conserva el texto íntegro', async () => {
  cargar('La resolución contiene otro criterio.')
  render(<LectorResolucion id={2} fragmento="Fragmento de una versión anterior." onClose={vi.fn()} />)
  expect((await screen.findByRole('status')).textContent).toContain('No se pudo localizar')
  expect(screen.getByRole('article', { name: 'Texto de la resolución' }).querySelector('mark')).toBeNull()
  expect(screen.getByText('La resolución contiene otro criterio.')).toBeTruthy()
})

it('una lectura desde el catálogo no muestra controles de relación con un caso', async () => {
  cargar('Texto general de la resolución.')
  render(<LectorResolucion id={3} onClose={vi.fn()} />)
  await screen.findByText('Texto general de la resolución.')
  expect(screen.queryByRole('button', { name: 'Ir al fragmento relacionado' })).toBeNull()
})
