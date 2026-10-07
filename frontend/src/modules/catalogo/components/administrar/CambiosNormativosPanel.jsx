import { useCallback, useEffect, useState } from 'react'
import normativaApi from '../../../../api/normativaApi'
import RevisionAviso from '../articulos/RevisionAviso'
import styles from '../articulos/Normativa.module.css'

function Cambio({ cambio, onActualizado, fundamentoCompartido = false }) {
  const historico = Boolean(cambio.aviso?.nota_historica)
  const informativo = historico || ['general', 'temporal'].includes(cambio.operacion)
  return <li>
    <strong>{cambio.operacion.toUpperCase()}</strong> · {cambio.norma_causante || cambio.fuente_nombre} · {cambio.fecha_norma_causante || 'Fecha por verificar'}
    <p>Disposición de origen: {cambio.disposicion_fuente || cambio.unidad_fuente}</p>
    {cambio.destino_catalogo && <p role="note">{cambio.destino_catalogo.mensaje}</p>}
    <p>Afecta: {cambio.referencia.norma || 'Norma del documento'} {cambio.referencia.unidad} · Alcance: {cambio.referencia.alcance}</p>
    {!fundamentoCompartido && <details><summary>Ver fundamento y fuente</summary><blockquote>{cambio.cita}</blockquote></details>}
    {cambio.url_fuente && <a href={cambio.url_fuente} target="_blank" rel="noopener noreferrer">Ver fuente oficial</a>}
    <p>{historico ? 'Nota histórica del texto incorporado' : informativo ? 'Aviso informativo' : cambio.estado_revision === 'pendiente' ? 'Pendiente de verificación' : cambio.estado_revision}</p>
    {historico && <p>{cambio.aviso.mensaje}</p>}
    {!informativo && cambio.estado_revision === 'pendiente' && ['deroga', 'abroga'].includes(cambio.operacion) &&
      <RevisionAviso aviso={{ ...cambio.aviso, id: cambio.id, operacion: cambio.operacion }} onActualizado={onActualizado} />}
  </li>
}
export default function CambiosNormativosPanel() {
  const [cambios, setCambios] = useState([])
  const [pagina, setPagina] = useState(1)
  const [siguiente, setSiguiente] = useState(false)
  const [estado, setEstado] = useState('pendiente')
  const [error, setError] = useState('')
  const refrescar = useCallback(async () => {
    try {
      const { data } = await normativaApi.cambios({ estado_revision: estado, page: pagina })
      setCambios(data.results || data); setSiguiente(Boolean(data.next)); setError('')
    } catch { setError('No se pudieron consultar los cambios normativos.') }
  }, [estado, pagina])
  useEffect(() => { refrescar() }, [refrescar])
  const grupos = Object.values(cambios.reduce((acc, c) => {
    const key = JSON.stringify([c.fuente, c.norma_causante, c.fecha_norma_causante, c.unidad_fuente, c.cita])
    ;(acc[key] ||= []).push(c)
    return acc
  }, {}))
  return <section className={styles.panel}>
    <h2>Verificar afectaciones normativas</h2>
    <p>Cada detección muestra su norma causante y la disposición de origen. Si el destino está cargado, confirma después de verificar la fuente, la fecha y el alcance. Si no está cargado, se conserva solo el aviso.</p>
    <label>Estado <select value={estado} onChange={(e) => { setEstado(e.target.value); setPagina(1) }}>
      <option value="pendiente">Pendientes</option><option value="confirmado">Confirmados</option><option value="descartado">Descartados</option>
    </select></label>{' '}<button type="button" onClick={refrescar}>Actualizar</button>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    {grupos.map((grupo) => <section key={grupo[0].id} aria-label={`Afectaciones de ${grupo[0].disposicion_fuente || grupo[0].unidad_fuente}`}>
      {grupo.length > 1 && <><h3>{grupo[0].norma_causante || grupo[0].fuente_nombre} · {grupo[0].disposicion_fuente || grupo[0].unidad_fuente}</h3>
        <p>{grupo.length} destinos distintos. Cada afectación se revisa por separado.</p>
        <details><summary>Ver fundamento común</summary><blockquote>{grupo[0].cita}</blockquote></details></>}
      <ul className={styles.lista}>{grupo.map((c) => <Cambio key={c.id} cambio={c} onActualizado={refrescar} fundamentoCompartido={grupo.length > 1} />)}</ul>
    </section>)}
    {!cambios.length && <p>No hay afectaciones en este estado.</p>}
    <button type="button" disabled={pagina <= 1} onClick={() => setPagina((p) => p-1)}>Anterior</button><span>Página {pagina}</span>
    <button type="button" disabled={!siguiente} onClick={() => setPagina((p) => p+1)}>Siguiente</button>
  </section>
}
