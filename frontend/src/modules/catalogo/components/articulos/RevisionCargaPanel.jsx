import normativaStyles from './Normativa.module.css'
import styles from '../../pages/articulos/CargaArticulosPage.module.css'

const ACCIONES = { nuevo: 'Nuevo', actualizar: 'Se actualizará', sin_cambios: 'Sin cambios de texto' }

export default function RevisionCargaPanel({ revision, modo, onModo, seleccion, onSeleccion, onConfirmar, onCancelar, enviando }) {
  const disposiciones = revision.disposiciones || []
  const completa = modo === 'completo'
  const elegidos = revision.articulos.filter((a) => completa || seleccion.includes(a.numero))
  const contar = (accion) => elegidos.filter((a) => a.accion === accion).length
  const toggle = (numero) => onSeleccion(seleccion.includes(numero) ? seleccion.filter((n) => n !== numero) : [...seleccion, numero])
  return <section className={styles.card} aria-labelledby="revision-titulo">
    <h2 id="revision-titulo" className={styles.cardTitle}>Revisar cambios · {revision.norma}</h2>
    <fieldset className={styles.modeOptions}>
      <legend>Cómo aplicar este PDF</legend>
      <label><input type="radio" name="modoActualizacion" checked={completa} onChange={() => onModo('completo')} />
        <strong>Reemplazar archivo completo</strong><span>El catálogo activo de esta norma y rama quedará basado en este PDF.
        Los artículos ausentes se retirarán y el PDF anterior quedará como historial.</span></label>
      <label><input type="radio" name="modoActualizacion" checked={!completa} onChange={() => onModo('articulos')} />
        <strong>Actualizar artículos seleccionados</strong><span>Elige los artículos que se añadirán o actualizarán.
        Los demás conservarán su contenido y su PDF fuente.</span></label>
    </fieldset>
    <p role="status" className={styles.reviewSummary}>
      {contar('actualizar')} por actualizar · {contar('nuevo')} nuevos · {contar('sin_cambios')} sin cambios de texto
      {completa && ` · ${revision.sobrantes.length} retirados del catálogo activo`}
    </p>
    <p>Una ausencia en el PDF no significa derogación. Los cambios detectados se registrarán para verificación, con el texto de respaldo.</p>
    {revision.motor === 'clasico' && <p className={styles.reviewWarning}>La lectura clásica detecta derogaciones y abrogaciones expresas de disposiciones con un destino inequívoco. Verifica las cláusulas ambiguas manualmente o usa Qwen.</p>}
    {revision.advertencias_lectura?.map((aviso, i) => <p key={i} role="note" className={styles.reviewWarning}>{aviso}</p>)}
    {revision.metadatos && <p>Norma principal: {revision.metadatos.tipo_norma} {revision.metadatos.numero_norma} · Fecha: {revision.metadatos.fecha_norma || 'por verificar'}.</p>}
    {Boolean(revision.cambios_normativos?.length) && <section role="alert" aria-label="Afectaciones normativas detectadas">
      <h3>{revision.cambios_normativos.length} efectos normativos detectados</h3>
      <ul>{revision.cambios_normativos.map((c, i) => <li key={i}>
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
    {!completa && <div className={styles.submitRow}>
      <button type="button" className={styles.btnSecondary} onClick={() => onSeleccion(revision.articulos.map((a) => a.numero))}>Seleccionar todos</button>
      <button type="button" className={styles.btnSecondary} onClick={() => onSeleccion([])}>Quitar selección</button>
    </div>}
    <div className={styles.reviewList}>
      {revision.articulos.map((a) => <div key={a.numero} className={styles.reviewArticle}>
        <label>{!completa && <input type="checkbox" checked={seleccion.includes(a.numero)} onChange={() => toggle(a.numero)}
          aria-label={`Seleccionar artículo ${a.numero}`} />}
          <strong>{a.tipo_unidad && a.tipo_unidad !== 'articulo' ? 'Disp. ' : 'Art. '}{a.numero}</strong> · {a.titulo} <span>{ACCIONES[a.accion]}</span></label>
        {a.derogado_en_pdf && <p className={styles.reviewWarning}>El PDF indica derogación o abrogación de este artículo.</p>}
        <details><summary>Comparar texto</summary>
          {a.texto_anterior && <p><strong>Anterior (fragmento):</strong> {a.texto_anterior}</p>}
          <p><strong>Nuevo (fragmento):</strong> {a.texto_nuevo}</p>
        </details>
      </div>)}
    </div>
    {revision.sobrantes.length > 0 && <details className={styles.reviewMissing}>
      <summary>{revision.sobrantes.length} artículos anteriores ausentes del PDF · {completa ? 'se retirarán' : 'se conservarán'}</summary>
      <ul>{revision.sobrantes.map((a) => <li key={a.numero}>Art. {a.numero} · {a.titulo || 'Sin epígrafe'}</li>)}</ul>
    </details>}
    <div className={styles.submitRow}>
      <button type="button" className={styles.btnSecondary} disabled={enviando} onClick={onCancelar}>Volver al formulario</button>
      <button type="button" className={styles.btnPrimary} disabled={enviando || (!elegidos.length && !disposiciones.length)} onClick={onConfirmar}>
        {enviando ? 'Enviando…' : completa ? 'Confirmar reemplazo completo' : `Confirmar ${elegidos.length} artículos${disposiciones.length ? ` y ${disposiciones.length} disposiciones` : ''}`}
      </button>
    </div>
  </section>
}
