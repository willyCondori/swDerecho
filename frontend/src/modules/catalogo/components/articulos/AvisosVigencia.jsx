import catalogoApi from '../../../../api/catalogoApi'
import styles from './Normativa.module.css'

export default function AvisosVigencia({ avisos = [] }) {
  if (!avisos.length) return null
  const descargar = async (id) => {
    try {
      const { data } = await catalogoApi.descargarDocumentoNorma(id)
      const url = URL.createObjectURL(data)
      const a = document.createElement('a')
      a.href = url; a.download = `fuente-normativa-${id}.pdf`; a.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch { window.alert('No se pudo descargar la fuente. Vuelve a intentarlo.') }
  }
  return <div className={styles.avisos} aria-label="Avisos de vigencia normativa">
    {avisos.map((a) => <aside key={a.id} role="note" className={styles.aviso}>
      <strong>{a.estado === 'confirmado' ? (a.operacion === 'deroga' ? (a.parte_afectada?.tipo === 'parcial' ? 'Derogación parcial confirmada' : 'Derogación confirmada') : a.operacion === 'abroga' ? 'Abrogación confirmada' : 'Afectación verificada') : a.estado === 'futuro' ? 'Efecto futuro' : 'Revisión pendiente'}</strong>
      <p>{a.mensaje}</p>
      {a.disposicion_fuente && <p>Disposición de origen: {a.disposicion_fuente}</p>}
      {a.parte_afectada?.tipo === 'parcial' && <div>
        <p><strong>Parte afectada: {a.parte_afectada.descripcion}</strong></p>
        {a.parte_afectada.partes?.map((p, i) => <div key={i}>
          {p.fragmento ? <details><summary>Texto de {p.descripcion}</summary><blockquote>{p.fragmento}</blockquote></details>
            : <p>{p.es_nueva_parte ? 'Nueva parte incorporada; consulte la fuente modificatoria.' : 'No se ha localizado inequívocamente el fragmento. Requiere revisión del artículo y la fuente.'}</p>}
        </div>)}
      </div>}
      {a.fecha_efecto && <p>Fecha de efecto: {a.fecha_efecto}</p>}
      <details><summary>Ver fundamento y fuente</summary><blockquote>{a.cita}</blockquote>
        {a.url_fuente && <a href={a.url_fuente} target="_blank" rel="noopener noreferrer">Publicación de origen</a>}
        {a.documento_id && <button type="button" onClick={() => descargar(a.documento_id)}>Descargar PDF de respaldo</button>}
      </details>
    </aside>)}
  </div>
}
