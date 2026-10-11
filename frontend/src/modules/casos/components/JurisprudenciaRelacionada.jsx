import { useEffect, useRef, useState } from 'react'
import LectorResolucion from '../../jurisprudencia/components/LectorResolucion'
import casosApi from '../../../api/casosApi'
import BloquePlegable from './BloquePlegable'
import styles from '../pages/CasoDetailPage.module.css'

const MENSAJES = {
  pendiente: 'Analiza el caso para buscar jurisprudencia relacionada con los hechos.',
  sin_corpus: 'Todavía no hay resoluciones del TSJ cargadas. Un administrador debe sincronizar la jurisprudencia y después volver a analizar el caso.',
  sin_embeddings: 'La jurisprudencia necesita actualizarse para el modelo actual. Después de actualizarla, vuelve a analizar el caso.',
  fuera_cobertura: 'La colección disponible corresponde a materia Penal. Este caso pertenece a otra rama.',
  sin_coincidencias: 'No se encontraron fragmentos con suficiente similitud y relación jurídica en la colección disponible.',
}

export default function JurisprudenciaRelacionada({ casoId, estadoAnalisis, resultado, puedeEscribir = false, bloqueado = false }) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(false)
  const [cargando, setCargando] = useState(false)
  const [resolucionAbierta, setResolucionAbierta] = useState(null)
  const [valorando, setValorando] = useState(null)
  const [errorValoracion, setErrorValoracion] = useState('')
  const revision = useRef(0)
  const operacionActiva = useRef(null)

  useEffect(() => {
    revision.current += 1
    setValorando(null); setErrorValoracion(''); operacionActiva.current = null
    setResolucionAbierta(null)
    setDatos(null); setError(false); setCargando(false)
    if (!resultado || estadoAnalisis === 'procesando') return
    const controller = new AbortController()
    setCargando(true)
    setError(false)
    setDatos(null)
    casosApi.jurisprudencia(casoId, { signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setDatos(data) })
      .catch(() => { if (!controller.signal.aborted) setError(true) })
      .finally(() => { if (!controller.signal.aborted) setCargando(false) })
    return () => { controller.abort(); revision.current += 1 }
  }, [casoId, estadoAnalisis, resultado?.updated_at, !!resultado])

  const valorar = async (r, valor) => {
    if (!puedeEscribir || bloqueado || operacionActiva.current) return
    const operacion = {}, vigente = revision.current
    operacionActiva.current = operacion
    setValorando(r.id); setErrorValoracion('')
    let guardada = false
    try {
      await casosApi.valorarJurisprudencia(casoId, {
        ...(r.valoracion_id ? { valoracion_id: r.valoracion_id } : { resultado_id: r.id }), valor,
      })
      guardada = true
      const { data } = await casosApi.jurisprudencia(casoId)
      if (revision.current === vigente) setDatos(data)
    } catch (e) {
      if (revision.current === vigente) setErrorValoracion(guardada
        ? 'Se guardó la valoración, pero no se pudo actualizar la lista. Recarga la página.'
        : e.response?.data?.detail || 'No se pudo guardar la valoración. Vuelve a intentar.')
    } finally {
      if (operacionActiva.current === operacion) operacionActiva.current = null
      if (revision.current === vigente) setValorando(null)
    }
  }
  const ordenados = [...(datos?.resultados || [])].sort((a, b) => Number(Boolean(a.es_sugerencia)) - Number(Boolean(b.es_sugerencia)))
  const seleccionados = ordenados.filter(r => r.valoracion === 'util')
  const pendientes = ordenados.filter(r => !r.valoracion || r.valoracion === 'sin_valorar')
  const descartados = ordenados.filter(r => r.valoracion === 'no_util')
  const fila = (r) => <li className={styles.listItem} key={r.id}>
    <h4 className={styles.articuloNumero}>{r.numero || `Resolución TSJ ${r.fuente_id}`}</h4>
    {r.valoracion_desactualizada && <span className={`${styles.badge} ${styles.badgePending}`}>Valorada en un contexto anterior</span>}
    {r.es_sugerencia && <span className={`${styles.badge} ${styles.badgePending}`}>Recomendación complementaria</span>}
    <p>{r.sala} · {r.fecha || 'Sin fecha'}</p>
    {r.coincidencias?.length > 0 && <p>Relación identificada: {r.coincidencias.join(', ')}</p>}
    {r.motivo_recomendacion && <p>{r.motivo_recomendacion}</p>}
    {r.expediente && <p>Expediente: {r.expediente}</p>}
    {r.desactualizada && <p role="status">La fuente cambió. Vuelve a analizar para actualizar este fragmento.</p>}
    <blockquote className={styles.articuloContenido}>{r.fragmento}</blockquote>
    {puedeEscribir && <label className={styles.valoracion}>Utilidad para este caso
      <select aria-label={`Utilidad de la resolución ${r.numero || r.fuente_id}`} value={r.valoracion || 'sin_valorar'}
        disabled={valorando != null || bloqueado} onChange={e => valorar(r, e.target.value)}>
        <option value="sin_valorar">Sin valorar</option><option value="util">Útil</option><option value="no_util">No útil</option>
      </select>
      {valorando === r.id && <span role="status">Guardando…</span>}
    </label>}
    {puedeEscribir && r.valoracion === 'util' && r.valoracion_desactualizada && <button type="button"
      className={styles.btnSecondary} disabled={valorando != null || bloqueado}
      onClick={() => valorar(r, 'util')}>Confirmar utilidad para el contexto actual</button>}
    {r.registro_id && <><button type="button" className={styles.btnSecondary} onClick={() => setResolucionAbierta(r)}>Leer resolución completa</button> · </>}
    <a href={r.url_fuente} target="_blank" rel="noopener noreferrer">Consultar fuente TSJ</a>
    {r.url_pdf && <> · <a href={r.url_pdf} target="_blank" rel="noopener noreferrer">PDF oficial</a></>}
  </li>

  const estado = datos?.estado || 'pendiente'
  return (
    <>
    <BloquePlegable titulo="Jurisprudencia relacionada" icono="ti-gavel">
      {estadoAnalisis === 'procesando' ? <p>Buscando jurisprudencia durante el análisis...</p>
        : cargando ? <p>Cargando jurisprudencia...</p>
          : error ? <p role="alert">No se pudo cargar la jurisprudencia. Recarga la página para reintentar.</p>
            : <>
              {datos?.desactualizada && <p role="status">Estos resultados pertenecen a un análisis anterior. Vuelve a analizar el caso para actualizarlos.</p>}
              {MENSAJES[estado] && <p className={styles.emptyText}>{MENSAJES[estado]}</p>}
              {datos?.resultados?.length > 0 && <>
                <p className={styles.emptyText}>Resoluciones relacionadas con los hechos y términos jurídicos del caso. Las recomendaciones complementarias requieren revisar su pertinencia y contrastar la tentativa cuando corresponda.</p>
                {errorValoracion && <p role="alert" className={styles.errorBanner}>{errorValoracion}</p>}
                <BloquePlegable titulo="Jurisprudencia seleccionada" nivel={3} className={styles.jurisprudenciaGrupo}>
                  <p>Resoluciones marcadas como útiles para revisar este caso.</p>
                  {seleccionados.some(r => r.valoracion_desactualizada) && <p role="status">El contexto del caso o la fuente cambió. Estas resoluciones se conservan como referencia; revisa si siguen siendo pertinentes.</p>}
                  {!seleccionados.length && <p>No hay resoluciones seleccionadas.</p>}
                  <ol className={styles.list} aria-label="Jurisprudencia seleccionada">{seleccionados.map(fila)}</ol>
                </BloquePlegable>
                  {descartados.length > 0 && <BloquePlegable titulo={`Jurisprudencia descartada (${descartados.length})`}
                    nivel={3} className={styles.jurisprudenciaGrupo} abiertoInicial={false}>
                    <p>Las marcadas como «No útil» no se recomendarán al volver a analizar este caso. Puedes corregir la valoración.</p>
                    <ul className={styles.list} aria-label="Jurisprudencia descartada">{descartados.map(fila)}</ul>
                  </BloquePlegable>}
                <BloquePlegable titulo="Jurisprudencia sin valorar" nivel={3} className={styles.jurisprudenciaGrupo}>
                  <p>Marca cada resolución como «Útil» para seleccionarla o «No útil» para descartarla.</p>
                  {!pendientes.length && <p>No hay resoluciones pendientes de valorar.</p>}
                  <ol className={styles.list} aria-label="Jurisprudencia sin valorar">{pendientes.map(fila)}</ol>
                </BloquePlegable>
              </>}
            </>}
    </BloquePlegable>
      <LectorResolucion id={resolucionAbierta?.registro_id} fragmento={resolucionAbierta?.fragmento} onClose={() => setResolucionAbierta(null)} />
    </>
  )
}
