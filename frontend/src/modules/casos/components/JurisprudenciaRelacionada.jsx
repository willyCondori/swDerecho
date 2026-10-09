import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import casosApi from '../../../api/casosApi'
import styles from '../pages/CasoDetailPage.module.css'

const MENSAJES = {
  pendiente: 'Analiza el caso para buscar jurisprudencia relacionada con los hechos.',
  sin_corpus: 'Todavía no hay resoluciones del TSJ cargadas. Un administrador debe sincronizar la jurisprudencia y después volver a analizar el caso.',
  sin_embeddings: 'La jurisprudencia necesita actualizarse para el modelo actual. Después de actualizarla, vuelve a analizar el caso.',
  fuera_cobertura: 'La colección disponible corresponde a materia Penal. Este caso pertenece a otra rama.',
  sin_coincidencias: 'No se encontraron resoluciones que superen el umbral de similitud en la colección disponible.',
}

export default function JurisprudenciaRelacionada({ casoId, estadoAnalisis, resultado }) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(false)
  const [cargando, setCargando] = useState(false)

  useEffect(() => {
    if (!resultado || estadoAnalisis === 'procesando') return
    const controller = new AbortController()
    setCargando(true)
    setError(false)
    setDatos(null)
    casosApi.jurisprudencia(casoId, { signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setDatos(data) })
      .catch(() => { if (!controller.signal.aborted) setError(true) })
      .finally(() => { if (!controller.signal.aborted) setCargando(false) })
    return () => controller.abort()
  }, [casoId, estadoAnalisis, resultado?.updated_at, !!resultado])

  const estado = datos?.estado || 'pendiente'
  return (
    <section className={styles.card} aria-label="Jurisprudencia relacionada">
      <h2 className={styles.cardTitle}><i className="ti ti-gavel" aria-hidden="true" /> Jurisprudencia relacionada</h2>
      {estadoAnalisis === 'procesando' ? <p>Buscando jurisprudencia durante el análisis...</p>
        : cargando ? <p>Cargando jurisprudencia...</p>
          : error ? <p role="alert">No se pudo cargar la jurisprudencia. Recarga la página para reintentar.</p>
            : <>
              {datos?.desactualizada && <p role="status">Estos resultados pertenecen a un análisis anterior. Vuelve a analizar el caso para actualizarlos.</p>}
              {MENSAJES[estado] && <p className={styles.emptyText}>{MENSAJES[estado]}</p>}
              {datos?.resultados?.length > 0 && <>
                <p className={styles.emptyText}>Resoluciones de materia Penal ordenadas por similitud con los hechos. Revisa el contexto y la decisión de cada resolución.</p>
                <ol className={styles.list}>
                  {datos.resultados.map((r) => (
                    <li className={styles.listItem} key={r.id}>
                      <h3 className={styles.articuloNumero}>{r.numero || `Resolución TSJ ${r.fuente_id}`}</h3>
                      <p>{r.sala} · {r.fecha || 'Sin fecha'} · Coincidencia semántica: {Math.round(r.score_semantico * 100)}%</p>
                      {r.expediente && <p>Expediente: {r.expediente}</p>}
                      {r.desactualizada && <p role="status">La fuente cambió. Vuelve a analizar para actualizar este fragmento.</p>}
                      <blockquote className={styles.articuloContenido}>{r.fragmento}</blockquote>
                      {r.registro_id && <><Link to={`/jurisprudencia?resolucion=${r.registro_id}`}>Leer resolución completa</Link> · </>}
                      <a href={r.url_fuente} target="_blank" rel="noopener noreferrer">Consultar fuente TSJ</a>
                      {r.url_pdf && <> · <a href={r.url_pdf} target="_blank" rel="noopener noreferrer">PDF oficial</a></>}
                    </li>
                  ))}
                </ol>
              </>}
            </>}
    </section>
  )
}
