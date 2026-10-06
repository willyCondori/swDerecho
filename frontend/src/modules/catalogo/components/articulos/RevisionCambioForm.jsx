import { useState } from 'react'
import catalogoApi from '../../../../api/catalogoApi'
import normativaApi from '../../../../api/normativaApi'
import styles from './Normativa.module.css'

export default function RevisionCambioForm({ cambio, normas = [], onActualizado }) {
  const [fecha, setFecha] = useState(cambio.fecha_norma_causante || '')
  const [causanteFecha, setCausanteFecha] = useState(cambio.fecha_norma_causante || '')
  const destino = String(cambio.destino_catalogo?.norma_id || cambio.norma_afectada || '')
  const [fechaDestino, setFechaDestino] = useState('')
  const [fragmento, setFragmento] = useState('')
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const guardar = async (descartar) => {
    setOcupado(true); setError('')
    try {
      if (!descartar && fechaDestino && destino) await catalogoApi.actualizarNorma(destino, { fecha_norma: fechaDestino })
      const { data } = await normativaApi.revisarCambio(cambio.id, { descartar, ...(descartar ? {} : { fecha_efecto: fecha, ...(fragmento ? { fragmento_afectado: fragmento } : {}),
        ...(causanteFecha ? { fecha_norma_causante: causanteFecha } : {}),
        ...(destino ? { norma_afectada_id: Number(destino) } : {}) }) })
      onActualizado(data)
    } catch (e) {
      const datos = e.response?.data
      setError(datos?.detail || (datos && Object.values(datos).flat().join(' ')) || 'No se pudo revisar el cambio.')
    } finally { setOcupado(false) }
  }
  const historico = Boolean(cambio.aviso?.nota_historica)
  const informativo = historico || ['general', 'temporal'].includes(cambio.operacion)
  const confirmable = !informativo && Boolean(cambio.destino_catalogo?.encontrado)
  return <div className={styles.revision} aria-label="Confirmación de afectación normativa">
    {cambio.estado_revision === 'pendiente' && <>
      {!confirmable && !informativo && <p>Requiere identificar inequívocamente la norma o unidad afectada. Una cláusula general no deroga artículos concretos automáticamente.</p>}
      {confirmable && <>
        <div className={styles.controles}>
          <label>Norma afectada <select value={destino} disabled>
            <option value="">Seleccionar destino verificado</option>{normas.map((n) => <option key={n.id} value={n.id}>{n.nombre}</option>)}
          </select></label>
          <label>Fecha de la norma afectada, si falta <input type="date" value={fechaDestino} onChange={(e) => setFechaDestino(e.target.value)} /></label>
          <label>Fecha verificada de la norma causante <input type="date" value={causanteFecha} onChange={(e) => setCausanteFecha(e.target.value)} /></label>
        </div>
        {cambio.referencia.parte_afectada?.tipo === 'parcial' && <>
          {cambio.operacion === 'deroga' && <p>Al confirmar, esta parte se retirará del texto activo desde la fecha de efecto. El antes y después quedará en Historial de cambios.</p>}
          <p>Parte afectada: <strong>{cambio.referencia.parte_afectada.descripcion}</strong></p>
          {cambio.referencia.parte_afectada.partes?.map((p, i) => <blockquote key={i}>{p.fragmento || `${p.descripcion}: fragmento por identificar`}</blockquote>)}
          {!cambio.referencia.parte_afectada.localizado && <label><p>Fragmento exacto del artículo afectado, verificado contra la fuente</p>
            <textarea value={fragmento} onChange={(e) => setFragmento(e.target.value)} placeholder="Copia únicamente la parte derogada del texto original" /></label>}
        </>}
        <label>Fecha de efecto verificada <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} /></label>
        <button type="button" disabled={ocupado || !destino || !fecha || !causanteFecha} onClick={() => guardar(false)}>{cambio.operacion === 'deroga' ? 'Confirmar derogación' : cambio.operacion === 'abroga' ? 'Confirmar abrogación' : 'Confirmar afectación'}</button></>}
      <button type="button" disabled={ocupado} onClick={() => guardar(true)}>Descartar detección</button>
    </>}
    {error && <p role="alert" className={styles.error}>{error}</p>}
  </div>
}
