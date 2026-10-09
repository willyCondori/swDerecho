import { useEffect, useState } from 'react'
import Modal from '../../../components/ui/Modal'
import jurisprudenciaApi from '../../../api/jurisprudenciaApi'
import styles from '../pages/Jurisprudencia.module.css'

export default function LectorResolucion({ id, onClose }) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
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
      <article aria-label="Texto de la resolución" className={styles.texto}>{datos.texto}</article>
    </>}
  </Modal>
}
