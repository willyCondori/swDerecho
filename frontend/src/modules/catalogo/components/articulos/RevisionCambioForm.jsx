import shared from '../../../../styles/shared.module.css'
import ComparacionCambioArticulo from './ComparacionCambioArticulo'
import { useEffect, useState } from 'react'
import catalogoApi from '../../../../api/catalogoApi'
import normativaApi from '../../../../api/normativaApi'
import styles from './Normativa.module.css'

export default function RevisionCambioForm({ cambio, normas = [], onActualizado, onPendiente, onBusy }) {
  const [fecha, setFecha] = useState(cambio.fecha_norma_causante || '')
  const [causanteFecha, setCausanteFecha] = useState(cambio.fecha_norma_causante || '')
  const destino = String(cambio.destino_catalogo?.norma_id || cambio.norma_afectada || '')
  const [fechaDestino, setFechaDestino] = useState('')
  const [fragmento, setFragmento] = useState('')
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [preview, setPreview] = useState(null)
  const [previewError, setPreviewError] = useState('')
  const [cargandoPreview, setCargandoPreview] = useState(true)
  useEffect(() => {
    if (cambio.estado_revision !== 'pendiente' || !['deroga', 'abroga'].includes(cambio.operacion) || cambio.aviso?.nota_historica) {
      setCargandoPreview(false)
      return
    }
    let activo = true
    setCargandoPreview(true); setPreviewError(''); setPreview(null)
    const timer = setTimeout(() => {
      normativaApi.prepararRevision(cambio.id, fragmento ? { fragmento_afectado: fragmento } : {})
        .then(({ data }) => { if (activo) setPreview(data) })
        .catch((error) => { if (activo) setPreviewError(error.response?.data?.detail || 'No se pudo generar la vista previa. Vuelve a abrir la revisión.') })
        .finally(() => { if (activo) setCargandoPreview(false) })
    }, fragmento ? 300 : 0)
    return () => { activo = false; clearTimeout(timer) }
  }, [cambio.id, cambio.estado_revision, cambio.operacion, cambio.aviso?.nota_historica, fragmento])
  const guardar = async (descartar) => {
    setOcupado(true); onBusy?.(true); setError('')
    try {
      if (!descartar && fechaDestino && destino) await catalogoApi.actualizarNorma(destino, { fecha_norma: fechaDestino })
      const { data } = await normativaApi.revisarCambio(cambio.id, { descartar, ...(descartar ? {} : { fecha_efecto: fecha, ...(fragmento ? { fragmento_afectado: fragmento } : {}),
        ...(causanteFecha ? { fecha_norma_causante: causanteFecha } : {}),
        ...(destino ? { norma_afectada_id: Number(destino) } : {}) }) })
      onActualizado(data)
    } catch (e) {
      const datos = e.response?.data
      setError(datos?.detail || (datos && Object.values(datos).flat().join(' ')) || 'No se pudo revisar el cambio.')
    } finally { setOcupado(false); onBusy?.(false) }
  }
  const historico = Boolean(cambio.aviso?.nota_historica)
  const informativo = historico || ['general', 'temporal'].includes(cambio.operacion)
  const confirmable = !informativo && Boolean(cambio.destino_catalogo?.encontrado)
  return <div className={styles.revision} aria-label="Confirmación de afectación normativa">
    <dl>
      <dt>Norma afectada</dt><dd>{normas.find((n) => String(n.id) === destino)?.nombre || cambio.referencia.norma || 'Destino por verificar'}</dd>
      <dt>Artículo o unidad</dt><dd>{cambio.referencia.unidad || 'Toda la norma'}</dd>
      <dt>Parte exacta</dt><dd>{cambio.referencia.parte_afectada?.descripcion || cambio.referencia.alcance || 'Total'}</dd>
      <dt>Fuente</dt><dd>{cambio.norma_causante || cambio.fuente_nombre} · {cambio.disposicion_fuente || cambio.aviso?.disposicion_fuente} · {causanteFecha || 'Fecha por verificar'}</dd>
    </dl>
    <section aria-label="Vista previa del cambio">
      <h3>Antes y después previsto</h3>
      <p>Esta vista previa no modifica el catálogo. La confirmación vuelve a validar el destino, el texto y las fechas.</p>
      {cargandoPreview && <p role="status">Preparando vista previa…</p>}
      {previewError && <p role="alert">{previewError}</p>}
      {!cargandoPreview && preview?.articulos?.map((registro) => <details key={registro.articulo_id} open={preview.articulos.length === 1}>
        <summary>{registro.norma} · Artículo {registro.numero_articulo}</summary>
        <ComparacionCambioArticulo registro={registro} preview />
      </details>)}
      {!cargandoPreview && preview && !preview.articulos?.length && <p>La norma cambiará de estado; no tiene artículos cargados para comparar.</p>}
      {cambio.referencia.parte_afectada?.tipo !== 'parcial' && <p>El texto original se conservará. Se marcará como {cambio.operacion === 'abroga' ? 'abrogado' : 'derogado'} desde la fecha de efecto.</p>}
    </section>
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
        <button type="button" className={shared.btnPrimary} disabled={ocupado || cargandoPreview || !preview || !destino || !fecha || !causanteFecha} onClick={() => guardar(false)}>{cambio.operacion === 'deroga' ? 'Confirmar derogación' : cambio.operacion === 'abroga' ? 'Confirmar abrogación' : 'Confirmar afectación'}</button></>}
      <button type="button" className={shared.btnSecondary} disabled={ocupado} onClick={() => guardar(true)}>Descartar aviso</button>
      <button type="button" className={shared.btnSecondary} disabled={ocupado} onClick={onPendiente}>Dejar pendiente</button>
    </>}
    {error && <p role="alert" className={styles.error}>{error}</p>}
  </div>
}
