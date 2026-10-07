import { afterEach, expect, it } from 'vitest'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import DialogHost from './DialogHost'
import { dialogs, dialogStore } from './dialogs'
afterEach(() => { cleanup(); while (dialogStore.snapshot()) dialogStore.close(false) })
it('waits for a choice and resolves cancellation without applying an action', async () => {
  render(<DialogHost />)
  let answer
  act(() => { answer = dialogs.confirm('¿Eliminar el documento?') })
  expect(screen.getByRole('dialog').textContent).toContain('¿Eliminar el documento?')
  fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
  expect(await answer).toBe(false)
  expect(screen.queryByRole('dialog')).toBeNull()
})
it('queues messages and confirmation and supports keyboard cancellation', async () => {
  render(<DialogHost />)
  let first, second
  act(() => { first = dialogs.alert('No se pudo guardar.'); second = dialogs.confirm('¿Reintentar?') })
  expect(screen.queryByText('¿Reintentar?')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Entendido' }))
  expect(await first).toBe(true)
  expect(screen.getByText('¿Reintentar?')).toBeTruthy()
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' })
  expect(await second).toBe(false)
})
