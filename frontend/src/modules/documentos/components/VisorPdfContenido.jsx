import { useEffect, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/TextLayer.css'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import Modal from '../../../components/ui/Modal'
import catalogoApi from '../../../api/catalogoApi'
import documentosApi from '../../../api/documentosApi'
import shared from '../../../styles/shared.module.css'
import styles from './VisorPdf.module.css'

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()

export default function VisorPdfContenido({ documentoId, nombre, origen = 'norma', onClose }) {
  const [archivo, setArchivo] = useState({ url: '', error: '', loading: true })
  const [pagina, setPagina] = useState(1)
  const [paginas, setPaginas] = useState(0)
  const [zoom, setZoom] = useState(1)
  const [ancho, setAncho] = useState(600)
  const contenedor = useRef(null)

  useEffect(() => {
    const controller = new AbortController()
    let url = ''
    setArchivo({ url: '', error: '', loading: true })
    setPagina(1)
    setPaginas(0)
    setZoom(1)
    const cargar = async () => {
      try {
        const { data } = await (origen === 'caso'
          ? documentosApi.descargar(documentoId, controller.signal)
          : catalogoApi.descargarDocumentoNorma(documentoId, controller.signal))
        if (controller.signal.aborted) return
        url = URL.createObjectURL(data)
        setArchivo({ url, error: '', loading: false })
      } catch (e) {
        if (controller.signal.aborted) return
        const status = e?.response?.status
        setArchivo({ url: '', loading: false, error: status === 403
          ? 'No tienes permiso para ver este documento.' : status === 404
            ? 'El archivo ya no está disponible.' : 'No se pudo abrir el PDF. Vuelve a intentarlo.' })
      }
    }
    cargar()
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url) }
  }, [documentoId, origen])

  useEffect(() => {
    const nodo = contenedor.current
    if (!nodo) return
    const medir = () => setAncho(Math.max(180, nodo.clientWidth - 24))
    medir()
    const observer = new ResizeObserver(medir)
    observer.observe(nodo)
    return () => observer.disconnect()
  }, [])

  const falloLectura = () => setArchivo((prev) => ({ ...prev, error: 'No se pudo leer el PDF. Puede estar dañado o protegido con contraseña.' }))
  return <Modal open onClose={onClose} title={nombre || 'Documento PDF'} description="Lectura del documento dentro del sistema.">
    <div className={styles.toolbar} aria-label="Controles del PDF">
      <button type="button" className={shared.btnSecondary} disabled={!paginas || pagina <= 1} onClick={() => setPagina((p) => p - 1)}>Página anterior</button>
      <span aria-live="polite">Página {paginas ? pagina : '—'} de {paginas || '—'}</span>
      <button type="button" className={shared.btnSecondary} disabled={!paginas || pagina >= paginas} onClick={() => setPagina((p) => p + 1)}>Página siguiente</button>
      <label>Zoom <select aria-label="Zoom" className={shared.input} value={zoom} onChange={(e) => setZoom(Number(e.target.value))}>
        {[0.75, 1, 1.25, 1.5, 2].map((valor) => <option key={valor} value={valor}>{valor * 100}%</option>)}
      </select></label>
    </div>
    {archivo.loading && <p role="status">Abriendo PDF…</p>}
    {archivo.error && <p role="alert" className={shared.errorBanner}>{archivo.error}</p>}
    <div ref={contenedor} className={styles.viewport}>
      {archivo.url && !archivo.error && <Document file={archivo.url} loading="Cargando documento…" onLoadSuccess={({ numPages }) => setPaginas(numPages)} onLoadError={falloLectura} onSourceError={falloLectura}
        onPassword={falloLectura} externalLinkTarget="_blank" externalLinkRel="noopener noreferrer">
        <Page pageNumber={pagina} width={Math.round(ancho * zoom)} loading="Cargando página…" onRenderError={falloLectura} />
      </Document>}
    </div>
  </Modal>
}
