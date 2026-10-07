import { dialogs } from '../../../../components/ui/dialogs'
import { useId, useState } from 'react'
import catalogoApi from '../../../../api/catalogoApi'
import styles from './Normativa.module.css'
import RevisionAviso from './RevisionAviso'
import useAuthStore from '../../../auth/store/authStore'

const TIPOS = { todos: 'Todos', deroga: 'Derogaciones', abroga: 'Abrogaciones', historico: 'Históricos', modifica: 'Modificaciones', incorpora: 'Incorporaciones', judicial: 'Referencias judiciales', temporal: 'Vigencia y plazos', general: 'Otros avisos' }
function categoria(a) {
  if (a.categoria_aviso && TIPOS[a.categoria_aviso]) return a.categoria_aviso
  if (a.operacion === 'deroga' || a.operacion === 'abroga') return a.operacion
  if (a.nota_historica || /nota histórica/i.test(a.mensaje || '')) return 'historico'
  if (/referencia judicial|decisión constitucional/i.test(a.mensaje || '')) return 'judicial'
  return TIPOS[a.operacion] ? a.operacion : 'general'
}
function estadoAviso(a) {
  if (a.requiere_verificacion_fuente || /por verificar/.test(a.mensaje || '') || categoria(a) === 'historico' && a.operacion === 'general') return 'fuente'
  if (['historico', 'judicial', 'temporal', 'general'].includes(categoria(a))) return 'informativo'
  return a.estado || 'pendiente'
}

export default function AvisosVigencia({ avisos = [], permitirRevision = false, onActualizado }) {
  const admin = useAuthStore((s) => s.isAdmin())
  const listaId = useId()
  const [vista, setVista] = useState({ avisos: null, tipo: 'todos', estado: 'todos', cantidad: 0 })
  const actual = vista.avisos === avisos ? vista : { tipo: 'todos', estado: 'todos', cantidad: 0 }
  const cambiar = (cambio) => setVista({ ...actual, avisos, ...cambio })
  const filtrados = avisos.filter((a) => (actual.tipo === 'todos' || categoria(a) === actual.tipo) && (actual.estado === 'todos' || estadoAviso(a) === actual.estado))
  const visibles = Math.min(actual.cantidad, filtrados.length)
  if (!avisos.length) return null
  const descargar = async (id) => {
    try {
      const { data } = await catalogoApi.descargarDocumentoNorma(id)
      const url = URL.createObjectURL(data)
      const a = document.createElement('a')
      a.href = url; a.download = `fuente-normativa-${id}.pdf`; a.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch { dialogs.alert('No se pudo descargar la fuente. Vuelve a intentarlo.') }
  }
  return <div className={styles.avisos} aria-label="Avisos de vigencia normativa">
    <h3>{avisos.length} avisos normativos</h3>
    <div className={styles.controles}>
      <label>Tipo de aviso <select value={actual.tipo} onChange={(e) => cambiar({ tipo: e.target.value, cantidad: 0 })}>
        {Object.entries(TIPOS).map(([id, titulo]) => <option key={id} value={id}>{titulo} ({id === 'todos' ? avisos.length : avisos.filter((a) => categoria(a) === id).length})</option>)}
      </select></label>
      <label>Estado del aviso <select value={actual.estado} onChange={(e) => cambiar({ estado: e.target.value, cantidad: 0 })}>
        <option value="todos">Todos los estados</option><option value="pendiente">Pendientes de confirmación</option><option value="confirmado">Confirmados</option><option value="descartado">Descartados</option><option value="revertido">Restaurados</option><option value="futuro">Efectos futuros</option><option value="informativo">Informativos e históricos</option><option value="fuente">Fuente o fecha por verificar</option>
      </select></label>
    </div>
    <p role="status">Mostrando {visibles} de {filtrados.length} avisos del filtro · {avisos.length} en total.</p>
    <p>Derogaciones y abrogaciones detectadas requieren verificación; el tipo del aviso no significa que el efecto esté confirmado.</p>
    {visibles < filtrados.length && <button type="button" aria-controls={listaId} aria-expanded={visibles > 0} onClick={() => cambiar({ cantidad: visibles + 10 })}>Ver más</button>}
    {visibles < filtrados.length && <button type="button" aria-controls={listaId} onClick={() => cambiar({ cantidad: filtrados.length })}>Ver todos</button>}
    {visibles > 0 && <button type="button" aria-controls={listaId} onClick={() => cambiar({ cantidad: 0 })}>Ocultar</button>}
    {!filtrados.length && <p>No hay avisos que coincidan con estos filtros.</p>}
    <div id={listaId} hidden={visibles === 0}>
    {filtrados.slice(0, visibles).map((a) => <aside key={a.id} role="note" className={`${styles.aviso} ${styles['aviso_' + categoria(a)] || ''}`}>
      <p className={styles.tipoAviso}>{TIPOS[categoria(a)]}{a.operacion === 'deroga' || a.operacion === 'abroga' ? ` · ${a.estado === 'confirmado' ? 'Confirmado' : a.estado === 'futuro' ? 'Efecto futuro' : a.estado === 'revertido' ? 'Restaurado' : a.estado === 'descartado' ? 'Descartado' : 'Detectado, pendiente'}` : ''}</p>
      {estadoAviso(a) === 'fuente' && <p>Fuente o fecha por verificar: contrasta la nota con la publicación oficial.</p>}
      <strong>{a.nota_historica ? 'Nota histórica de la versión del PDF' : ['temporal', 'general'].includes(a.operacion) ? 'Aviso informativo' : a.estado === 'confirmado' ? (a.operacion === 'deroga' ? (a.parte_afectada?.tipo === 'parcial' ? 'Derogación parcial confirmada' : 'Derogación confirmada') : a.operacion === 'abroga' ? 'Abrogación confirmada' : 'Afectación verificada') : a.estado === 'futuro' ? 'Efecto futuro' : a.estado === 'revertido' ? 'Confirmación revertida' : a.estado === 'descartado' ? 'Detección descartada' : 'Revisión pendiente'}</strong>
      <p>{['temporal', 'general'].includes(a.operacion)
        ? (a.operacion === 'temporal' ? `Regla de vigencia o plazo de ${a.norma_causante || 'la fuente'}. No confirma la derogación de un artículo concreto.` : (a.mensaje || `Aviso para revisión de ${a.norma_causante || 'la fuente'}. No confirma la derogación de un artículo concreto.`))
        : categoria(a) === 'historico' && /norma causante por verificar/.test(a.mensaje || '') ? 'Antecedente histórico por revisar: la nota no identifica una fuente inequívoca o cita varias reformas. Verifica la secuencia de cambios en las publicaciones originales.' : a.mensaje}</p>
      {!a.nota_historica && !['temporal', 'general'].includes(a.operacion) && a.estado === 'pendiente' && <p>
        {a.destino_catalogo?.encontrado === false ? 'Solo aviso: el destino exacto no está cargado. Para aplicar el cambio, primero incorpore esa norma o artículo y luego revise el efecto en Catálogo → Normas.'
          : permitirRevision && admin && ['deroga', 'abroga'].includes(a.operacion)
            ? 'El aviso no cambia automáticamente la vigencia. Revisa la fuente y confirma el efecto aquí.'
            : 'El aviso no cambia automáticamente la vigencia. Un usuario autorizado debe revisar la fuente y confirmar el efecto en Catálogo → Normas.'}
      </p>}
      {a.disposicion_fuente && <p>Disposición de origen: {a.disposicion_fuente}</p>}
      {!a.nota_historica && !['temporal', 'general'].includes(a.operacion) && a.parte_afectada?.tipo === 'parcial' && <div>
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
      {permitirRevision && admin && a.id && !a.nota_historica && ['deroga', 'abroga'].includes(a.operacion) && a.estado === 'pendiente' && a.destino_catalogo?.encontrado &&
        <RevisionAviso aviso={a} onActualizado={onActualizado} />}
    </aside>)}
    </div>
  </div>
}
