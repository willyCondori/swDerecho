import { useCallback, useEffect, useState } from 'react'
import normativaApi from '../../../../api/normativaApi'
import styles from './Normativa.module.css'

export default function GacetaPanel({ onElegir }) {
  const [documentos, setDocumentos] = useState([])
  const [pagina, setPagina] = useState(1)
  const [siguiente, setSiguiente] = useState(false)
  const [tarea, setTarea] = useState(() => sessionStorage.getItem('gaceta-task'))
  useEffect(() => { if (tarea) sessionStorage.setItem('gaceta-task', tarea); else sessionStorage.removeItem('gaceta-task') }, [tarea])
  const [resumen, setResumen] = useState(null)
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(() => Boolean(sessionStorage.getItem('gaceta-task')))
  const [maxPaginas, setMaxPaginas] = useState(1)
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const refrescar = useCallback(async () => {
    const { data } = await normativaApi.documentos({ page: pagina })
    setDocumentos(data.results || data); setSiguiente(Boolean(data.next))
  }, [pagina])
  useEffect(() => { refrescar().catch(() => setError('No se pudo consultar los documentos de Gaceta.')) }, [refrescar])
  useEffect(() => {
    if (!tarea) return
    let cancelado = false
    let timer
    const consultar = async () => {
      try {
        const { data } = await normativaApi.estado(tarea)
        if (cancelado) return
        setResumen(data.resultado || data.resumen || null)
        if (data.estado === 'SUCCESS') {
          setTarea(null); setOcupado(false); await refrescar(); return
        }
        if (data.estado === 'FAILURE') {
          setError(data.error); setTarea(null); setOcupado(false); return
        }
        timer = setTimeout(consultar, 2000)
      } catch {
        if (!cancelado) { setError('No se pudo consultar el progreso. La tarea puede continuar en el servidor.'); setTarea(null); setOcupado(false) }
      }
    }
    consultar()
    return () => { cancelado = true; clearTimeout(timer) }
  }, [tarea, refrescar])
  const sincronizar = async () => {
    setOcupado(true); setError(''); setResumen(null)
    try {
      const { data } = await normativaApi.sincronizar({ max_paginas: Number(maxPaginas), ...(desde ? { desde } : {}), ...(hasta ? { hasta } : {}) })
      setTarea(data.task_id)
    } catch (e) { setError(e.response?.data?.detail || 'No se pudo iniciar la sincronización.'); setOcupado(false) }
  }
  const elegir = async (documento, importar) => {
    setOcupado(true); setError('')
    try {
      const { data } = await normativaApi.descargar(documento.id)
      const archivo = new File([data], `${documento.tipo}-${documento.numero || documento.identificador}.pdf`, { type: 'application/pdf' })
      if (importar) await onElegir(documento, archivo)
      else {
        const url = URL.createObjectURL(data)
        const a = document.createElement('a'); a.href = url; a.download = archivo.name; a.click()
        setTimeout(() => URL.revokeObjectURL(url), 1000)
      }
    } catch (e) { setError(e.message || 'No se pudo descargar el PDF original.') }
    finally { setOcupado(false) }
  }
  return <section className={styles.panel} aria-label="Gaceta Oficial de Bolivia">
    <h2>Documentos penales de la Gaceta Oficial</h2>
    <p>Consulta leyes, decretos y otros documentos disponibles. La búsqueda revisa también el texto completo.
      Los archivos descargados se conservan; sus efectos se revisan al incorporarlos al catálogo.</p>
    <div className={styles.controles}>
      <label>Páginas por listado (0 = todas)<input type="number" min="0" value={maxPaginas} onChange={(e) => setMaxPaginas(e.target.value)} /></label>
      <label>Publicado desde<input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} /></label>
      <label>Publicado hasta<input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} /></label>
      <button type="button" disabled={ocupado || maxPaginas === ''} onClick={sincronizar}>{tarea ? 'Sincronizando…' : 'Buscar y descargar de la Gaceta'}</button>
    </div>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    {resumen && <div role="status"><p>{resumen.consultados} consultados · {resumen.descargados} PDFs descargados · {resumen.existentes} ya registrados · {resumen.paginas} páginas.
      {resumen.cobertura === 'parcial' && ' Cobertura parcial: consulta el límite elegido y los errores.'}</p>
      {Boolean(resumen.errores?.length) && <details><summary>{resumen.errores.length} publicaciones o listados pendientes</summary>
        <ul>{resumen.errores.map((e, i) => <li key={i}><a href={e.url} target="_blank" rel="noopener noreferrer">Fuente</a>: {e.error}</li>)}</ul>
      </details>}
    </div>}
    <ul className={styles.lista}>{documentos.map((d) => <li key={d.id}>
      <strong>{d.titulo}</strong> · Publicación: {d.fecha_publicacion || 'por verificar'}
      <p>{d.estado_descarga === 'descargado' ? 'PDF conservado' : `Descarga pendiente: ${d.error}`}{d.documento_catalogo && ' · Ya incorporado al catálogo'}</p>
      <a href={d.url_fuente} target="_blank" rel="noopener noreferrer">Ver publicación oficial</a>{' '}
      <button type="button" disabled={ocupado || d.estado_descarga !== 'descargado'} onClick={() => elegir(d, false)}>Descargar PDF</button>
      {onElegir && <button type="button" disabled={ocupado || d.estado_descarga !== 'descargado'} onClick={() => elegir(d, true)}>Revisar e incorporar</button>}
    </li>)}</ul>
    {!documentos.length && <p>Aún no hay documentos penales descargados en esta página.</p>}
    <button type="button" disabled={pagina <= 1 || ocupado} onClick={() => setPagina((p) => p-1)}>Anterior</button>
    <span>Página {pagina}</span>
    <button type="button" disabled={!siguiente || ocupado} onClick={() => setPagina((p) => p+1)}>Siguiente</button>
  </section>
}
