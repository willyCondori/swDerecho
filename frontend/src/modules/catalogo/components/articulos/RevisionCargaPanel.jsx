import { useId, useState } from 'react'
import normativaStyles from './Normativa.module.css'
import styles from '../../pages/articulos/CargaArticulosPage.module.css'

const ACCIONES = { nuevo: 'Nuevo', actualizar: 'Se actualizará', sin_cambios: 'Sin cambios de texto' }

export default function RevisionCargaPanel({ revision, modo, onModo, seleccion, onSeleccion, onConfirmar, onCancelar, enviando, onSeccion, onAlternativa, onIdentidad, soloVista = false, onIdentidadSeccion, onAlternativaSeccion }) {
  const panelId = useId()
  const tituloId = `${panelId}-titulo`
  const efectosId = `${panelId}-efectos`
  const comparacionId = `${panelId}-comparacion`
  const listaArticulosId = `${panelId}-articulos`
  const [identidad, setIdentidad] = useState({ nombre: '', numero: '', fecha: '' })
  const [vistaEfectos, setVistaEfectos] = useState({ revision: null, cantidad: 0 })
  const efectos = revision.cambios_normativos || []
  const visibles = vistaEfectos.revision === revision ? Math.min(vistaEfectos.cantidad, efectos.length) : 0
  const mostrarEfectos = (cantidad) => setVistaEfectos({ revision, cantidad })
  const [vistaArticulos, setVistaArticulos] = useState({ revision: null, cantidad: 0 })
  const articulosVisibles = vistaArticulos.revision === revision ? Math.min(vistaArticulos.cantidad, revision.articulos.length) : 0
  const mostrarArticulos = (cantidad) => setVistaArticulos({ revision, cantidad })
  const disposiciones = revision.disposiciones || []
  const anexos = revision.anexos || []
  const pendientesAnexos = anexos.some((a) => (!a.articulos.length && !a.disposiciones?.length) || a.identidad_por_verificar || (a.unidades_ambiguas || []).some((u) => !u.seleccionada))
  const completa = modo === 'completo'
  const pendientes = (revision.unidades_ambiguas || []).filter((u) => !u.seleccionada)
  const elegidos = revision.articulos.filter((a) => completa || seleccion.includes(a.numero))
  const contar = (accion) => elegidos.filter((a) => a.accion === accion).length
  const toggle = (numero) => onSeleccion(seleccion.includes(numero) ? seleccion.filter((n) => n !== numero) : [...seleccion, numero])
  return <section className={styles.card} aria-labelledby={tituloId}>
    <h2 id={tituloId} className={styles.cardTitle}>Revisar cambios · {revision.norma}</h2>
    {revision.secciones_documento?.length > 1 && !anexos.length && <section aria-label="Normas identificadas en el PDF">
      <p>Este PDF contiene varias normas. Se revisa y carga una norma por vez conservando el archivo original.</p>
      <label>Norma del PDF <select aria-label="Norma del PDF" value={revision.seccion_activa} onChange={(e) => onSeccion?.(e.target.value)} disabled={enviando}>
        {revision.secciones_documento.map((s) => <option key={s.id} value={s.id}>{s.titulo || revision.norma}</option>)}
      </select></label>
    </section>}
    {revision.documento_fuente && <section className={styles.reviewSummary} aria-label="Identidad del documento fuente">
      <strong>Documento fuente: {revision.documento_fuente.nombre || revision.documento_fuente.titulo_cabecera}</strong>
      <p>{revision.documento_fuente.tipo_norma} {revision.documento_fuente.numero_norma} · Fecha del documento: {revision.documento_fuente.fecha_norma || 'por verificar'}</p>
      {revision.identidad_por_verificar && <p>Esta fecha pertenece a la ley modificatoria. La norma destinataria conserva su propio número y fecha.</p>}
    </section>}
    {revision.identidad_por_verificar && <fieldset>
      <legend>Identificar la norma destinataria del extracto</legend>
      <p>El título puede corresponder a una ley modificatoria. Contrasta la norma a la que pertenecen estos artículos con la fuente antes de continuar.</p>
      <label>Nombre de la norma destinataria <input value={identidad.nombre} onChange={(e) => setIdentidad({ ...identidad, nombre: e.target.value })} disabled={enviando} /></label>
      <label>Número legal de la norma destinataria <input value={identidad.numero} onChange={(e) => setIdentidad({ ...identidad, numero: e.target.value })} disabled={enviando} /></label>
      <label>Fecha de la norma destinataria <input type="date" value={identidad.fecha} onChange={(e) => setIdentidad({ ...identidad, fecha: e.target.value })} disabled={enviando} /></label>
      <button type="button" disabled={enviando || !identidad.nombre.trim() || !identidad.numero.trim() || !identidad.fecha} onClick={() => onIdentidad?.(identidad)}>Revisar extracto con esta identidad</button>
    </fieldset>}
    {(revision.unidades_ambiguas || []).map((u) => <fieldset key={u.clave} aria-label={`Alternativas de ${u.numero}`}>
      <legend>{u.tipo_unidad === 'articulo' ? 'Artículo' : 'Disposición'} {u.numero}: textos distintos en el PDF</legend>
      <p>Compara las versiones con el original. Solo se importará la alternativa que selecciones.</p>
      {u.alternativas.map((a, i) => <div key={a.id_unidad}>
        <label><input type="radio" name={u.clave} checked={u.seleccionada === a.id_unidad} onChange={() => onAlternativa?.(u.clave, a.id_unidad)} disabled={enviando} />Alternativa {i + 1}</label>
        <details><summary>Ver texto completo de alternativa {i + 1}</summary><p style={{ whiteSpace: 'pre-wrap' }}>{a.texto}</p></details>
      </div>)}
      <label><input type="radio" name={u.clave} checked={u.seleccionada === 'ignorar'} onChange={() => onAlternativa?.(u.clave, 'ignorar')} disabled={enviando} />No importar esta unidad</label>
    </fieldset>)}
    {pendientes.length > 0 && <p role="alert">Hay {pendientes.length} unidades pendientes de revisión. No se puede reemplazar el catálogo completo hasta resolverlas.</p>}
    {!soloVista && <fieldset className={styles.modeOptions}>
      <legend>Cómo aplicar este PDF</legend>
      <label><input type="radio" name="modoActualizacion" disabled={revision.fragmento_normativo || revision.identidad_por_verificar} checked={completa} onChange={() => onModo('completo')} />
        <strong>Reemplazar archivo completo</strong><span>El catálogo activo de esta norma y rama quedará basado en este PDF.
        Los artículos ausentes se retirarán y el PDF anterior quedará como historial.</span></label>
      <label><input type="radio" name="modoActualizacion" checked={!completa} onChange={() => onModo('articulos')} />
        <strong>Actualizar artículos seleccionados</strong><span>Elige los artículos que se añadirán o actualizarán.
        Los demás conservarán su contenido y su PDF fuente.</span></label>
    </fieldset>}
    <p>{revision.secciones_documento?.length || 1} normas identificadas en el PDF · {1 + anexos.length} normas para cargar · {disposiciones.length} disposiciones para guardar.</p>
    {revision.fragmento_normativo && <p role="note">Esta sección es un extracto. Se guardará en su norma propia; usa actualización de artículos seleccionados. Los demás artículos se conservan.</p>}
    <p role="status" className={styles.reviewSummary}>
      {contar('actualizar')} por actualizar · {contar('nuevo')} nuevos · {contar('sin_cambios')} sin cambios de texto
      {completa && ` · ${revision.sobrantes.length} retirados del catálogo activo`}
    </p>
    <p>Una ausencia en el PDF no significa derogación. Los cambios detectados se registrarán para verificación, con el texto de respaldo.</p>
    {revision.motor === 'clasico' && <p className={styles.reviewWarning}>La lectura por algoritmos detecta modificaciones, incorporaciones, derogaciones y abrogaciones expresas. Los destinos o alcances ambiguos permanecen como avisos para revisión manual.</p>}
    {revision.advertencias_lectura?.map((aviso, i) => <p key={i} role="note" className={styles.reviewWarning}>{aviso}</p>)}
    {revision.metadatos && <p>Norma principal: {revision.metadatos.tipo_norma} {revision.metadatos.numero_norma} · Fecha: {revision.metadatos.fecha_norma || 'por verificar'}.</p>}
    {Boolean(revision.cambios_normativos?.length) && <section role="alert" aria-label="Afectaciones normativas detectadas">
      <h3>{revision.cambios_normativos.length} efectos normativos detectados</h3>
      <div className={styles.submitRow}>
        {visibles < efectos.length && <button type="button" className={styles.btnSecondary} aria-expanded={visibles > 0} aria-controls={efectosId} onClick={() => mostrarEfectos(Math.min(visibles + 10, efectos.length))}>Ver más</button>}
        {visibles < efectos.length && <button type="button" className={styles.btnSecondary} aria-controls={efectosId} onClick={() => mostrarEfectos(efectos.length)}>Ver todo</button>}
        {visibles > 0 && <button type="button" className={styles.btnSecondary} aria-controls={efectosId} onClick={() => mostrarEfectos(0)}>Ocultar</button>}
      </div>
      {visibles > 0 && <p>Mostrando {visibles} de {efectos.length} efectos normativos.</p>}
      <ul id={efectosId} hidden={visibles === 0}>{efectos.slice(0, visibles).map((c, i) => <li key={i}>
        <strong>{c.operacion.toUpperCase()}</strong> · Fuente: {c.norma_causante || revision.norma}, {c.disposicion_fuente || c.unidad_fuente} · {c.norma || 'Norma de este documento'} {c.unidad} · {c.alcance}
        {c.destino_catalogo && <p role="note">{c.destino_catalogo.mensaje}</p>}
        <blockquote>{c.cita}</blockquote>
        {c.origen === 'nota_editorial' && <p>Nota histórica: {c.causante} · {c.fecha_causante}</p>}
      </li>)}</ul><p>Los efectos de las disposiciones se registran siempre; los de artículos, si están seleccionados. Cargar el PDF no confirma derogaciones ni abrogaciones; si el destino existe, podrás confirmarlas en Verificar afectaciones normativas.</p>
    </section>}
    {disposiciones.length > 0 && <section aria-label="Disposiciones del documento">
      <h3>Disposiciones finales, derogatorias y abrogatorias</h3>
      <p>Se guardarán separadas de los artículos. No se importan disposiciones transitorias.</p>
      <div className={normativaStyles.tablaContenedor}><table className={normativaStyles.tabla}><thead><tr><th>Tipo</th><th>Disposición</th><th>Texto</th></tr></thead>
        <tbody>{disposiciones.map((d) => <tr key={d.numero}><td>{d.tipo_unidad}</td><td>{d.numero}</td>
          <td><details><summary>Ver disposición</summary><p style={{ whiteSpace: 'pre-wrap' }}>{d.texto}</p></details></td></tr>)}</tbody>
      </table></div>
    </section>}
    <section aria-labelledby={comparacionId}>
      <h3 id={comparacionId}>Comparación de artículos anteriores y nuevos</h3>
      <p>{revision.articulos.length} artículos para revisar.</p>
      <div className={styles.submitRow}>
        {articulosVisibles < revision.articulos.length && <button type="button" className={styles.btnSecondary} aria-expanded={articulosVisibles > 0} aria-controls={listaArticulosId} onClick={() => mostrarArticulos(Math.min(articulosVisibles + 10, revision.articulos.length))}>Ver más</button>}
        {articulosVisibles < revision.articulos.length && <button type="button" className={styles.btnSecondary} aria-controls={listaArticulosId} onClick={() => mostrarArticulos(revision.articulos.length)}>Ver todo</button>}
        {articulosVisibles > 0 && <button type="button" className={styles.btnSecondary} aria-controls={listaArticulosId} onClick={() => mostrarArticulos(0)}>Ocultar</button>}
      </div>
      {articulosVisibles > 0 && <p>Mostrando {articulosVisibles} de {revision.articulos.length} artículos.</p>}
    {!completa && !soloVista && <div className={styles.submitRow}>
      <button type="button" className={styles.btnSecondary} onClick={() => onSeleccion(revision.articulos.map((a) => a.numero))}>Seleccionar todos</button>
      <button type="button" className={styles.btnSecondary} onClick={() => onSeleccion([])}>Quitar selección</button>
    </div>}
    <div id={listaArticulosId} className={styles.reviewList} hidden={articulosVisibles === 0}>
      {revision.articulos.slice(0, articulosVisibles).map((a) => <div key={a.numero} className={styles.reviewArticle}>
        <label>{!completa && !soloVista && <input type="checkbox" checked={seleccion.includes(a.numero)} onChange={() => toggle(a.numero)}
          aria-label={`Seleccionar artículo ${a.numero}`} />}
          <strong>{a.tipo_unidad && a.tipo_unidad !== 'articulo' ? 'Disp. ' : 'Art. '}{a.numero}</strong> · {a.titulo} <span>{ACCIONES[a.accion]}</span></label>
        {a.derogado_en_pdf && <p className={styles.reviewWarning}>El PDF indica derogación o abrogación de este artículo.</p>}
        <details><summary>Comparar texto</summary>
          {a.texto_anterior && <p><strong>Anterior (fragmento):</strong> {a.texto_anterior}</p>}
          <p><strong>Nuevo (fragmento):</strong> {a.texto_nuevo}</p>
        </details>
      </div>)}
    </div>
    </section>
    {revision.sobrantes.length > 0 && <details className={styles.reviewMissing}>
      <summary>{revision.sobrantes.length} artículos anteriores ausentes del PDF · {completa ? 'se retirarán' : 'se conservarán'}</summary>
      <ul>{revision.sobrantes.map((a) => <li key={a.numero}>Art. {a.numero} · {a.titulo || 'Sin epígrafe'}</li>)}</ul>
    </details>}
    {anexos.length > 0 && <section aria-label="Otras normas que se cargarán por separado">
      <h3>{anexos.length} normas adicionales del PDF</h3>
      <p>Se cargarán los artículos y disposiciones de cada anexo en su propia norma, conservando los artículos ausentes. Resuelve los destinos y las alternativas pendientes antes de confirmar toda la carga.</p>
      {anexos.map((a) => <RevisionCargaPanel key={a.seccion_activa} revision={a} modo="articulos" soloVista seleccion={a.articulos.map((u) => u.numero)} enviando={enviando}
        onIdentidad={(identidad) => onIdentidadSeccion?.(a.seccion_activa, identidad)}
        onAlternativa={(clave, id) => onAlternativaSeccion?.(a.seccion_activa, clave, id)} />)}
    </section>}
    {pendientesAnexos && <p role="alert">Hay anexos con identidad o versiones pendientes. Resuélvelos antes de cargar todas las normas.</p>}
    {!soloVista && <div className={styles.submitRow}>
      <button type="button" className={styles.btnSecondary} disabled={enviando} onClick={onCancelar}>Volver al formulario</button>
      <button type="button" className={styles.btnPrimary} disabled={enviando || pendientesAnexos || revision.identidad_por_verificar || (completa && revision.fragmento_normativo) || (completa && pendientes.length > 0) || (!elegidos.length && !disposiciones.length)} onClick={onConfirmar}>
        {enviando ? 'Enviando…' : anexos.length ? `Confirmar carga de ${1 + anexos.length} normas` : completa ? 'Confirmar reemplazo completo' : `Confirmar ${elegidos.length} artículos${disposiciones.length ? ` y ${disposiciones.length} disposiciones` : ''}`}
      </button>
    </div>}
  </section>
}
