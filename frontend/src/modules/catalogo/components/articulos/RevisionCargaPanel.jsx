import styles from '../../pages/articulos/CargaArticulosPage.module.css'

const ACCIONES = { nuevo: 'Nuevo', actualizar: 'Se actualizará', sin_cambios: 'Sin cambios de texto' }

export default function RevisionCargaPanel({ revision, modo, onModo, seleccion, onSeleccion, onConfirmar, onCancelar, enviando }) {
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
    {revision.motor === 'clasico' && <p className={styles.reviewWarning}>La lectura clásica no analiza efectos jurídicos con IA. Verifica las disposiciones manualmente o vuelve al formulario y elige Qwen.</p>}
    {revision.advertencias_lectura?.map((aviso, i) => <p key={i} role="note" className={styles.reviewWarning}>{aviso}</p>)}
    {revision.metadatos && <p>Norma principal: {revision.metadatos.tipo_norma} {revision.metadatos.numero_norma} · Fecha: {revision.metadatos.fecha_norma || 'por verificar'}.</p>}
    {Boolean(revision.cambios_normativos?.length) && <details open>
      <summary>{revision.cambios_normativos.length} efectos normativos detectados</summary>
      <ul>{revision.cambios_normativos.map((c, i) => <li key={i}>
        <strong>{c.operacion.toUpperCase()}</strong> · Fuente: {c.unidad_fuente} · {c.norma || 'Norma de este documento'} {c.unidad} · {c.alcance}
        <blockquote>{c.cita}</blockquote>
        {c.origen === 'nota_editorial' && <p>Nota histórica: {c.causante} · {c.fecha_causante}</p>}
      </li>)}</ul><p>Solo se registrarán efectos contenidos en las unidades elegidas.</p>
    </details>}
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
      <button type="button" className={styles.btnPrimary} disabled={enviando || !elegidos.length} onClick={onConfirmar}>
        {enviando ? 'Enviando…' : completa ? 'Confirmar reemplazo completo' : `Confirmar ${elegidos.length} artículos`}
      </button>
    </div>
  </section>
}
