import { fireEvent, render, screen, cleanup, within } from '@testing-library/react'
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
  fireEvent.click(within(screen.getByRole('region', { name: 'Comparación de artículos anteriores y nuevos' })).getByRole('button', { name: 'Ver todo' }))
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


it('muestra la norma causante, la disposición exacta y el aviso de destino ausente', () => {
  render(<RevisionCargaPanel revision={{ ...revision, cambios_normativos: [{ operacion: 'abroga',
    norma: 'Ley 11080', unidad: '', alcance: 'total', norma_causante: 'Ley 2298',
    disposicion_fuente: 'disposición final tercera', cita: 'Queda abrogada la Ley 11080.',
    destino_catalogo: { encontrado: false, mensaje: 'Solo aviso: la norma no está cargada.' } }] }}
    modo="articulos" onModo={vi.fn()} seleccion={['1']} onSeleccion={vi.fn()} onConfirmar={vi.fn()} onCancelar={vi.fn()} />)
  fireEvent.click(within(screen.getByRole('alert', { name: 'Afectaciones normativas detectadas' })).getByRole('button', { name: 'Ver todo' }))
  expect(screen.getByText(/Fuente: Ley 2298, disposición final tercera/)).toBeTruthy()
  expect(screen.getByText('Solo aviso: la norma no está cargada.')).toBeTruthy()
  expect(screen.getByText(/Cargar el PDF no confirma derogaciones ni abrogaciones/)).toBeTruthy()
})


it('separa las disposiciones en tabla y permite cargarlas sin seleccionar artículos', () => {
  const datos = { ...revision, disposiciones: [{ numero: 'DD ÚNICA', tipo_unidad: 'derogatoria',
    texto: 'Se derogan el Parágrafo III del Artículo 323 Bis y el Artículo 281 Quater.' }],
    cambios_normativos: [{ operacion: 'deroga', norma: 'Código Penal', unidad: '323 BIS', alcance: 'Parágrafo III',
      norma_causante: 'Ley 1636', disposicion_fuente: 'disposición derogatoria única', cita: 'Se deroga el Parágrafo III.' }] }
  render(<RevisionCargaPanel revision={datos} modo="articulos" seleccion={[]} onModo={vi.fn()}
    onSeleccion={vi.fn()} onConfirmar={vi.fn()} onCancelar={vi.fn()} />)
  expect(screen.getByRole('table')).toBeTruthy()
  fireEvent.click(within(screen.getByRole('alert', { name: 'Afectaciones normativas detectadas' })).getByRole('button', { name: 'Ver todo' }))
  expect(screen.getByRole('alert', { name: 'Afectaciones normativas detectadas' }).textContent).toContain('Parágrafo III')
  expect(screen.queryByRole('checkbox', { name: 'Seleccionar artículo DD ÚNICA' })).toBeNull()
  expect(screen.getByRole('button', { name: 'Confirmar 0 artículos y 1 disposiciones' }).disabled).toBe(false)
})


it('permite revisar otra norma del mismo PDF sin volver a subir otro archivo', () => {
  const onSeccion = vi.fn()
  render(<RevisionCargaPanel revision={{ ...revision, seccion_activa: '0',
    secciones_documento: [{ id: '0', titulo: 'Código Penal' }, { id: '1', titulo: 'Ley 1333' }] }}
    modo="articulos" seleccion={['1']} onModo={vi.fn()} onSeleccion={vi.fn()} onCancelar={vi.fn()} onConfirmar={vi.fn()} onSeccion={onSeccion} />)
  fireEvent.change(screen.getByRole('combobox', { name: 'Norma del PDF' }), { target: { value: '1' } })
  expect(onSeccion).toHaveBeenCalledWith('1')
})

it('las versiones repetidas requieren elegir una alternativa antes de reemplazar todo', () => {
  const onAlternativa = vi.fn()
  render(<RevisionCargaPanel revision={{ ...revision, unidades_ambiguas: [{ clave: 'articulo:1', numero: '1', tipo_unidad: 'articulo', seleccionada: '',
    alternativas: [{ id_unidad: 'antes', texto: 'Texto anterior íntegro' }, { id_unidad: 'despues', texto: 'Texto nuevo íntegro' }] }] }}
    modo="completo" seleccion={['1']} onModo={vi.fn()} onSeleccion={vi.fn()} onCancelar={vi.fn()} onConfirmar={vi.fn()} onAlternativa={onAlternativa} />)
  expect(screen.getByRole('button', { name: 'Confirmar reemplazo completo' }).disabled).toBe(true)
  fireEvent.click(screen.getByRole('radio', { name: 'Alternativa 2' }))
  expect(onAlternativa).toHaveBeenCalledWith('articulo:1', 'despues')
  expect(screen.getByText('Texto anterior íntegro')).toBeTruthy()
  expect(screen.getByText('Texto nuevo íntegro')).toBeTruthy()
})

it('permite identificar el destinatario de un extracto sin habilitar reemplazo completo', () => {
  const onIdentidad = vi.fn()
  render(<RevisionCargaPanel revision={{ ...revision, fragmento_normativo: true, identidad_por_verificar: true }} modo="articulos" seleccion={['1']} onIdentidad={onIdentidad} />)
  expect(screen.getByRole('radio', { name: /Reemplazar archivo completo/ }).disabled).toBe(true)
  expect(screen.getByRole('button', { name: 'Confirmar 1 artículos' }).disabled).toBe(true)
  fireEvent.change(screen.getByLabelText('Nombre de la norma destinataria'), { target: { value: 'Ley de Pensiones' } })
  fireEvent.change(screen.getByLabelText('Número legal de la norma destinataria'), { target: { value: '065' } })
  fireEvent.change(screen.getByLabelText('Fecha de la norma destinataria'), { target: { value: '2010-12-10' } })
  fireEvent.click(screen.getByRole('button', { name: 'Revisar extracto con esta identidad' }))
  expect(onIdentidad).toHaveBeenCalledWith({ nombre: 'Ley de Pensiones', numero: '065', fecha: '2010-12-10' })
})
