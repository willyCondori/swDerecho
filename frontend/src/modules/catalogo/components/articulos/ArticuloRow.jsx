import { useId, useState } from 'react'
import TextoVigencia from './TextoVigencia'
import AvisosVigencia from './AvisosVigencia'
import catalogoApi from '../../../../api/catalogoApi'
import { getRamaKey } from '../../utils/rama'
import JerarquiaNivel from './JerarquiaNivel'
import TextoResaltado from './TextoResaltado'
import styles from '../../pages/articulos/VerArticulos.module.css'

export default function ArticuloRow({ articulo, busqueda = '' }) {
  const [expandido, setExpandido] = useState(false)
  const textoId = useId()
  const contenido = articulo.contenido || ''
  const [aviso, setAviso] = useState('')
  const [documentos, setDocumentos] = useState(null)
  const [cargandoPdf, setCargandoPdf] = useState(false)
  const rama = articulo.rama?.nombre || articulo.rama_nombre || '—'
  const norma = articulo.norma?.nombre || articulo.norma_nombre || '—'
  const sigla = articulo.norma?.sigla || articulo.norma_sigla
  const titulo = articulo.titulo === `Art. ${articulo.numero_articulo}` ? 'Sin epígrafe'
    : articulo.titulo?.replace(/^Art\.\s+\d+(?:\s+\w+)?\s*-\s*/i, '') || 'Sin epígrafe'
  const derogado = /\b(?:DEROGAD[OA]|ABROGAD[OA])\b/i.test(titulo)

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(articulo.contenido || '')
      setAviso('Artículo copiado')
    } catch {
      setAviso('No se pudo copiar. Puedes seleccionar el texto y copiarlo manualmente.')
    }
  }
  const descargar = async (id) => {
    setCargandoPdf(true)
    setAviso('')
    try {
      const { data } = await catalogoApi.descargarDocumentoNorma(id)
      const url = URL.createObjectURL(data)
      const enlace = document.createElement('a')
      enlace.href = url
      enlace.download = `norma-${id}.pdf`
      enlace.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch {
      setAviso('No se pudo descargar el PDF. Vuelve a intentarlo.')
    } finally { setCargandoPdf(false) }
  }
  const verPdf = async () => {
    if (articulo.documento_norma_id) return descargar(articulo.documento_norma_id)
    setCargandoPdf(true)
    try {
      const id = articulo.norma?.id || articulo.norma_id
      if (!id) { setAviso('Este artículo todavía no tiene un PDF fuente asociado.'); return }
      const { data } = await catalogoApi.documentosPorNorma(id)
      setDocumentos(Array.isArray(data) ? data : data.results || [])
      setAviso('El artículo no tiene una fuente individual registrada. Elige un PDF de su norma.')
    } catch { setAviso('No se pudieron consultar los PDF. Vuelve a intentarlo.') }
    finally { setCargandoPdf(false) }
  }

  return <>
    <tr className={styles.tr}>
      <td className={styles.td}><span className={styles.numPill}>{articulo.tipo_unidad && articulo.tipo_unidad !== 'articulo' ? 'Disp. ' : 'Art. '}{articulo.numero_articulo}</span></td>
      <td className={styles.td}><h2 className={styles.articleTitle}><TextoResaltado texto={titulo} busqueda={busqueda} /></h2>
        {derogado && <span className={styles.legalStatus}>El PDF indica derogación o abrogación</span>}</td>
      <td className={styles.td}><span className={`${styles.ramaBadge} ${styles[getRamaKey(rama)]}`}>{rama}</span></td>
      <td className={styles.td}><div className={styles.normaCell}><span>{norma}</span>{sigla && <small>{sigla}</small>}</div></td>
      <td className={styles.td}><JerarquiaNivel nivel={articulo.norma?.jerarquia?.nivel ?? articulo.jerarquia_nivel}
        nombre={articulo.norma?.jerarquia?.nombre ?? articulo.jerarquia_nombre} /></td>
    </tr>
    <tr className={styles.articleBodyRow}><td colSpan={5}>
      <AvisosVigencia avisos={articulo.avisos_vigencia} />
      <div id={textoId} hidden={!expandido}>
      <div hidden={!expandido} className={styles.articleText}>
        {expandido && <TextoVigencia texto={contenido || 'Sin texto disponible.'} avisos={articulo.avisos_vigencia} busqueda={busqueda} />}
      </div>
      {expandido && <>
      <div className={styles.articleActions}>
        <button type="button" className={styles.btnSecondary} onClick={copiar}>Copiar artículo</button>
        <button type="button" className={styles.btnSecondary} disabled={cargandoPdf} onClick={verPdf}>
          {cargandoPdf ? 'Consultando PDF…' : 'PDF original'}</button>
      </div>
      <p role="status" className={styles.articleNotice}>{aviso}</p>
      {documentos && <div className={styles.articleActions}>
        {documentos.length === 0 ? <span>No hay PDF disponibles para esta norma.</span> : documentos.map((d) =>
          <button type="button" key={d.id} disabled={cargandoPdf} className={styles.btnSecondary}
            onClick={() => descargar(d.id)}>{d.nombre_original}{d.vigente === false ? ' (histórico)' : ''}</button>)}
      </div>}
      </>}
      </div>
      {contenido && <button type="button" className={styles.expandBtn} aria-expanded={expandido}
        aria-controls={textoId} onClick={() => setExpandido((actual) => !actual)}>
        {expandido ? 'Ver menos' : 'Ver más'}
      </button>}
    </td></tr>
  </>
}
