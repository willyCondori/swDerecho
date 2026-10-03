import { fireEvent, render, screen, cleanup } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import RevisionCargaPanel from './RevisionCargaPanel'

afterEach(cleanup)
const revision = { norma: 'Norma de prueba', articulos: [
  { numero: '1', titulo: 'Objeto', accion: 'actualizar', texto_anterior: 'Anterior', texto_nuevo: 'Nuevo' },
  { numero: '2', titulo: 'Derogado', accion: 'nuevo', derogado_en_pdf: true, texto_nuevo: '(Derogado)' },
], sobrantes: [{ numero: '99', titulo: 'Anterior ausente' }] }

it('distingue retirar del catálogo de derogar y permite elegir el modo completo', () => {
  const onModo = vi.fn()
  render(<RevisionCargaPanel revision={revision} modo="articulos" onModo={onModo} seleccion={['1']}
    onSeleccion={vi.fn()} onConfirmar={vi.fn()} onCancelar={vi.fn()} />)
  expect(screen.getByText(/se conservarán/)).toBeTruthy()
  expect(screen.getByText(/Una ausencia en el PDF no significa derogación/)).toBeTruthy()
  fireEvent.click(screen.getByRole('radio', { name: /Reemplazar archivo completo/ }))
  expect(onModo).toHaveBeenCalledWith('completo')
  expect(screen.getByRole('checkbox', { name: 'Seleccionar artículo 1' }).checked).toBe(true)
  expect(screen.getByRole('checkbox', { name: 'Seleccionar artículo 2' }).checked).toBe(false)
})

it('impide confirmar una actualización selectiva vacía', () => {
  render(<RevisionCargaPanel revision={revision} modo="articulos" onModo={vi.fn()} seleccion={[]}
    onSeleccion={vi.fn()} onConfirmar={vi.fn()} onCancelar={vi.fn()} />)
  expect(screen.getByRole('button', { name: 'Confirmar 0 artículos' }).disabled).toBe(true)
})

it('el modo completo incluye todo el PDF y muestra los artículos que se retirarán', () => {
  render(<RevisionCargaPanel revision={revision} modo="completo" onModo={vi.fn()} seleccion={[]}
    onSeleccion={vi.fn()} onConfirmar={vi.fn()} onCancelar={vi.fn()} />)
  expect(screen.getByText(/1 por actualizar · 1 nuevos/)).toBeTruthy()
  expect(screen.getByText(/artículos anteriores ausentes del PDF · se retirarán/)).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Confirmar reemplazo completo' }).disabled).toBe(false)
})
