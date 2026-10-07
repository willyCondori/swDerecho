import { useSearchParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import normativaApi from '../../../../api/normativaApi'
import catalogoApi from '../../../../api/catalogoApi'
import ComparacionCambioArticulo from '../articulos/ComparacionCambioArticulo'
import styles from '../articulos/Normativa.module.css'

export default function HistorialArticulosPanel() {
  const [params, setParams] = useSearchParams()
  const articulo = params.get('articulo') || ''
  const [registros, setRegistros] = useState([])
  const [normas, setNormas] = useState([])
  const [norma, setNorma] = useState('')
  const [operacion, setOperacion] = useState('')
  const [pagina, setPagina] = useState(1)
  const [siguiente, setSiguiente] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  useEffect(() => { catalogoApi.normas().then(({ data }) => setNormas(data.results || data)).catch(() => {}) }, [])
  useEffect(() => {
    let cancelado = false
    setLoading(true); setError('')
    normativaApi.historial({ ...(articulo ? { articulo } : {}), ...(norma ? { norma } : {}), ...(operacion ? { operacion } : {}), page: pagina })
      .then(({ data }) => {
        if (!cancelado) { setRegistros(data.results || data); setSiguiente(Boolean(data.next)) }
      }).catch(() => { if (!cancelado) setError('No se pudo consultar el historial de cambios.') })
      .finally(() => { if (!cancelado) setLoading(false) })
    return () => { cancelado = true }
  }, [norma, operacion, pagina, revision, articulo])
  const descargar = async (id) => {
    try {
      const { data } = await catalogoApi.descargarDocumentoNorma(id)
      const url = URL.createObjectURL(data)
      const enlace = document.createElement('a')
      enlace.href = url; enlace.download = `fuente-normativa-${id}.pdf`; enlace.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch { setError('No se pudo descargar el PDF de respaldo.') }
  }
  return <section className={styles.panel}>
    <h2>Historial de cambios de artículos</h2>
    <p>Consulta los efectos confirmados, la parte afectada y las versiones anterior y posterior. Los textos originales se conservan como respaldo.</p>
    {articulo && <p>Historial del artículo seleccionado. <button type="button" onClick={() => { setParams({}); setPagina(1) }}>Ver todos los artículos</button></p>}
    <div className={styles.controles}>
      <label>Norma <select value={norma} onChange={(e) => { setNorma(e.target.value); setPagina(1) }}>
        <option value="">Todas las normas</option>{normas.map((n) => <option key={n.id} value={n.id}>{n.nombre}</option>)}
      </select></label>
      <label>Tipo de cambio <select value={operacion} onChange={(e) => { setOperacion(e.target.value); setPagina(1) }}>
        <option value="">Todos</option><option value="deroga">Derogaciones</option><option value="abroga">Abrogaciones</option>
      </select></label>
      <button type="button" disabled={loading} onClick={() => setRevision((v) => v + 1)}>Actualizar historial</button>
    </div>
    {error && <p role="alert">{error}</p>}
    {loading ? <p role="status">Consultando historial…</p> : <>
      {!registros.length && !error && <p>No hay cambios confirmados en este filtro.</p>}
      <ul className={styles.lista}>{registros.map((h) => <li key={h.id}>
        <h3>{h.norma} · Artículo {h.numero_articulo}</h3>
        <p><strong>{h.operacion === 'abroga' ? 'Abrogación' : h.parte_afectada?.tipo === 'parcial' ? 'Derogación parcial' : 'Derogación total'}</strong> por {h.norma_causante} · Fecha de efecto: {h.fecha_efecto}</p>
        <p>Parte afectada: {h.parte_afectada?.descripcion || 'Artículo completo'} · Origen: {h.disposicion_fuente}</p>
        {h.estado_revision === 'revertido' && <p>Restaurado por {h.restaurado_por} · {new Date(h.restaurado_at).toLocaleString('es-BO')}. Se conserva la comparación del cambio original.</p>}
        <p>{h.estado_revision === 'revertido' ? 'Esta confirmación fue revertida; ya no aplica al texto activo.' : !h.aplicado ? 'Programado: todavía no aplicado al texto activo.' : h.texto_antes !== h.texto_despues ? 'Parte derogada retirada del texto activo.' : 'Vigencia actualizada; el texto completo se conserva para consulta histórica.'}</p>
        <p>Confirmado por {h.revisado_por}{h.revisado_at && ` · ${new Date(h.revisado_at).toLocaleString('es-BO')}`}</p>
        <details><summary>Ver antes y después</summary>
          <ComparacionCambioArticulo registro={h} />
        </details>
        <details><summary>Ver parte afectada y fuente</summary>
          {h.parte_afectada?.partes?.map((p, i) => <blockquote key={i}>{p.fragmento || p.descripcion}</blockquote>)}
          <blockquote>{h.cita}</blockquote>
          <button type="button" onClick={() => descargar(h.documento_id)}>Descargar PDF de respaldo</button>
        </details>
      </li>)}</ul>
      <button type="button" disabled={pagina <= 1} onClick={() => setPagina((p) => p - 1)}>Anterior</button>
      <span>Página {pagina}</span>
      <button type="button" disabled={!siguiente} onClick={() => setPagina((p) => p + 1)}>Siguiente</button>
    </>}
  </section>
}
