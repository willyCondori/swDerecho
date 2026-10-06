import { useState } from 'react'
import normativaApi from '../../../../api/normativaApi'
import catalogoApi from '../../../../api/catalogoApi'
import RevisionCambioForm from './RevisionCambioForm'

export default function RevisionAviso({ aviso, onActualizado }) {
  const [cambio, setCambio] = useState(null)
  const [normas, setNormas] = useState([])
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState('')
  const abrir = async () => {
    setOcupado(true); setError('')
    try {
      const [actual, destinos] = await Promise.all([normativaApi.cambio(aviso.id), catalogoApi.normas()])
      setCambio(actual.data)
      setNormas(destinos.data.results || destinos.data)
      // El efecto puede haberse revisado desde otra pantalla o sesión.
      if (actual.data.estado_revision !== 'pendiente') onActualizado?.(actual.data.aviso)
    } catch {
      setError('No se pudo consultar la afectación actual. Vuelve a intentarlo.')
    } finally { setOcupado(false) }
  }
  return <section aria-label="Revisar efecto detectado">
    {!cambio && <button type="button" disabled={ocupado} onClick={abrir}>
      {ocupado ? 'Consultando afectación…' : aviso.operacion === 'abroga' ? 'Revisar y confirmar abrogación' : 'Revisar y confirmar derogación'}
    </button>}
    {error && <p role="alert">{error}</p>}
    {cambio && <>
      <p><strong>{cambio.norma_causante}</strong> · {cambio.fecha_norma_causante || 'Fecha por verificar'}</p>
      <p>Destino: {cambio.referencia.norma || 'Norma del documento'} · {cambio.referencia.unidad} · Alcance: {cambio.referencia.alcance}</p>
      <details><summary>Fuente verificada para esta confirmación</summary><blockquote>{cambio.cita}</blockquote></details>
      <p>{cambio.destino_catalogo?.mensaje}</p>
      {cambio.estado_revision === 'pendiente'
        ? <RevisionCambioForm cambio={cambio} normas={normas} onActualizado={(actual) => {
            setCambio(actual)
            onActualizado?.(actual.aviso)
          }} />
        : <p role="status">Revisión registrada: {cambio.estado_revision}.</p>}
      <button type="button" onClick={() => setCambio(null)}>Cerrar revisión</button>
    </>}
  </section>
}
