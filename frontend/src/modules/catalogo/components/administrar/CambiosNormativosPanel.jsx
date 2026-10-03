import { useCallback, useEffect, useState } from 'react'
import catalogoApi from '../../../../api/catalogoApi'
import normativaApi from '../../../../api/normativaApi'
import styles from '../articulos/Normativa.module.css'

function Cambio({ cambio, normas, onActualizado }) {
  const [fecha, setFecha] = useState(cambio.fecha_norma_causante || '')
  const [causanteFecha, setCausanteFecha] = useState(cambio.fecha_norma_causante || '')
  const destino = String(cambio.destino_catalogo?.norma_id || cambio.norma_afectada || '')
  const [fechaDestino, setFechaDestino] = useState('')
  const [fragmento, setFragmento] = useState('')
  const [observacion, setObservacion] = useState('')
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const guardar = async (descartar) => {
    setOcupado(true); setError('')
    try {
      if (!descartar && fechaDestino && destino) await catalogoApi.actualizarNorma(destino, { fecha_norma: fechaDestino })
      await normativaApi.revisarCambio(cambio.id, { descartar, ...(descartar ? {} : { fecha_efecto: fecha, observacion, ...(fragmento ? { fragmento_afectado: fragmento } : {}),
        ...(causanteFecha ? { fecha_norma_causante: causanteFecha } : {}),
        ...(destino ? { norma_afectada_id: Number(destino) } : {}) }) })
      onActualizado()
    } catch (e) {
      const datos = e.response?.data
      setError(datos?.detail || (datos && Object.values(datos).flat().join(' ')) || 'No se pudo revisar el cambio.')
    } finally { setOcupado(false) }
  }
  const confirmable = !['general', 'temporal'].includes(cambio.operacion) && Boolean(cambio.destino_catalogo?.encontrado)
  return <li>
    <strong>{cambio.operacion.toUpperCase()}</strong> · {cambio.norma_causante || cambio.fuente_nombre} · {cambio.fecha_norma_causante || 'Fecha por verificar'}
    <p>Disposición de origen: {cambio.disposicion_fuente || cambio.unidad_fuente}</p>
    {cambio.destino_catalogo && <p role="note">{cambio.destino_catalogo.mensaje}</p>}
    <p>Afecta: {cambio.referencia.norma || 'Norma del documento'} {cambio.referencia.unidad} · Alcance: {cambio.referencia.alcance}</p>
    <blockquote>{cambio.cita}</blockquote>
    {cambio.url_fuente && <a href={cambio.url_fuente} target="_blank" rel="noopener noreferrer">Ver fuente oficial</a>}
    <p>{cambio.estado_revision === 'pendiente' ? 'Pendiente de verificación' : cambio.estado_revision}</p>
    {cambio.estado_revision === 'pendiente' && <>
      {!confirmable && <p>Requiere identificar inequívocamente la norma o unidad afectada. Una cláusula general no deroga artículos concretos automáticamente.</p>}
      {confirmable && <>
        <div className={styles.controles}>
          <label>Norma afectada <select value={destino} disabled>
            <option value="">Seleccionar destino verificado</option>{normas.map((n) => <option key={n.id} value={n.id}>{n.nombre}</option>)}
          </select></label>
          <label>Fecha de la norma afectada, si falta <input type="date" value={fechaDestino} onChange={(e) => setFechaDestino(e.target.value)} /></label>
          <label>Fecha verificada de la norma causante <input type="date" value={causanteFecha} onChange={(e) => setCausanteFecha(e.target.value)} /></label>
        </div>
        {cambio.referencia.parte_afectada?.tipo === 'parcial' && <>
          <p>Parte afectada: <strong>{cambio.referencia.parte_afectada.descripcion}</strong></p>
          {cambio.referencia.parte_afectada.partes?.map((p, i) => <blockquote key={i}>{p.fragmento || `${p.descripcion}: fragmento por identificar`}</blockquote>)}
          {!cambio.referencia.parte_afectada.localizado && <label><p>Fragmento exacto del artículo afectado, verificado contra la fuente</p>
            <textarea value={fragmento} onChange={(e) => setFragmento(e.target.value)} placeholder="Copia únicamente la parte derogada del texto original" /></label>}
        </>}
        <label>Fecha de efecto verificada <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} /></label>
        <label><p>Fundamento de la revisión</p><textarea value={observacion} onChange={(e) => setObservacion(e.target.value)} placeholder="Verificación de fecha, alcance, competencia y vigencia" /></label>
        <button type="button" disabled={ocupado || !destino || !fecha || !causanteFecha || !observacion.trim()} onClick={() => guardar(false)}>{cambio.operacion === 'deroga' ? 'Confirmar derogación' : cambio.operacion === 'abroga' ? 'Confirmar abrogación' : 'Confirmar afectación'}</button></>}
      <button type="button" disabled={ocupado} onClick={() => guardar(true)}>Descartar detección</button>
    </>}
    {error && <p role="alert" className={styles.error}>{error}</p>}
  </li>
}
export default function CambiosNormativosPanel() {
  const [cambios, setCambios] = useState([])
  const [normas, setNormas] = useState([])
  useEffect(() => { catalogoApi.normas().then(({ data }) => setNormas(data.results || data)).catch(() => {}) }, [])
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
  return <section className={styles.panel}>
    <h2>Verificar afectaciones normativas</h2>
    <p>Cada detección muestra su norma causante y la disposición de origen. Si el destino está cargado, confirma después de verificar la fuente, la fecha y el alcance. Si no está cargado, se conserva solo el aviso.</p>
    <label>Estado <select value={estado} onChange={(e) => { setEstado(e.target.value); setPagina(1) }}>
      <option value="pendiente">Pendientes</option><option value="confirmado">Confirmados</option><option value="descartado">Descartados</option>
    </select></label>{' '}<button type="button" onClick={refrescar}>Actualizar</button>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    <ul className={styles.lista}>{cambios.map((c) => <Cambio key={c.id} cambio={c} normas={normas} onActualizado={refrescar} />)}</ul>
    {!cambios.length && <p>No hay afectaciones en este estado.</p>}
    <button type="button" disabled={pagina <= 1} onClick={() => setPagina((p) => p-1)}>Anterior</button><span>Página {pagina}</span>
    <button type="button" disabled={!siguiente} onClick={() => setPagina((p) => p+1)}>Siguiente</button>
  </section>
}
