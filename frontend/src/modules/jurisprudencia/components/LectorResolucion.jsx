import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Modal from '../../../components/ui/Modal'
import jurisprudenciaApi from '../../../api/jurisprudenciaApi'
import styles from '../pages/Jurisprudencia.module.css'
import shared from '../../../styles/shared.module.css'
import localizarFragmento from '../utils/localizarFragmento'

export default function LectorResolucion({ id, fragmento, onClose }) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
  const [mostrarResaltado, setMostrarResaltado] = useState(true)
  const textoRef = useRef(null)
  const marcaRef = useRef(null)
  const rango = useMemo(() => localizarFragmento(datos?.texto, fragmento), [datos?.texto, fragmento])
  const irAlFragmento = useCallback(() => {
    const contenedor = textoRef.current, marca = marcaRef.current
    if (!contenedor || !marca) return
    const top = contenedor.scrollTop + marca.getBoundingClientRect().top - contenedor.getBoundingClientRect().top - contenedor.clientHeight / 3
    contenedor.scrollTop = Math.max(0, top)
  }, [])
  useEffect(() => { setMostrarResaltado(true) }, [id, fragmento])
  useEffect(() => { if (id && rango && mostrarResaltado) irAlFragmento() }, [id, rango, mostrarResaltado, irAlFragmento])
  useEffect(() => {
    if (!id) return
    const controller = new AbortController()
    setDatos(null); setError('')
    jurisprudenciaApi.obtener(id, { signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setDatos(data) })
      .catch(() => { if (!controller.signal.aborted) setError('No se pudo abrir la resolución. Cierra la ventana e intenta nuevamente.') })
    return () => controller.abort()
  }, [id])
  return <Modal open={Boolean(id)} onClose={onClose} title={datos?.numero || 'Resolución del TSJ'} description="Texto completo de la resolución conservada en SW Derecho.">
    {error ? <p role="alert">{error}</p> : !datos ? <p>Cargando resolución...</p> : <>
      <p>{datos.sala} · {datos.fecha || 'Sin fecha'} · {datos.departamento}</p>
      {datos.expediente && <p>Expediente: {datos.expediente}</p>}
      <div className={styles.enlaces}><a href={datos.url_fuente} target="_blank" rel="noopener noreferrer">Fuente oficial</a>
        {datos.url_pdf && <a href={datos.url_pdf} target="_blank" rel="noopener noreferrer">PDF oficial</a>}</div>
      {fragmento && <div className={styles.relacion}>
        {rango ? <>
          <p>Fragmento relacionado recuperado por el análisis del caso. Revisa su pertinencia jurídica.</p>
          <div className={styles.enlaces}>
            <button type="button" className={shared.btnSecondary} onClick={() => { setMostrarResaltado(true); irAlFragmento() }}>Ir al fragmento relacionado</button>
            <button type="button" className={shared.btnSecondary} aria-pressed={mostrarResaltado} onClick={() => setMostrarResaltado(v => !v)}>{mostrarResaltado ? 'Ocultar resaltado' : 'Mostrar resaltado'}</button>
          </div>
        </> : <p role="status">No se pudo localizar el fragmento del análisis en esta versión de la resolución. Se muestra el texto completo sin resaltado.</p>}
      </div>}
      <article ref={textoRef} aria-label="Texto de la resolución" className={styles.texto}>
        {rango ? <>{datos.texto.slice(0, rango.inicio)}<mark ref={marcaRef} className={mostrarResaltado ? styles.fragmentoRelacionado : styles.fragmentoSinResaltar}>{datos.texto.slice(rango.inicio, rango.fin)}</mark>{datos.texto.slice(rango.fin)}</> : datos.texto}
      </article>
    </>}
  </Modal>
}
