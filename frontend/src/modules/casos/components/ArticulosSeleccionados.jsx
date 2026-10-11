import TextoVigencia from '../../catalogo/components/articulos/TextoVigencia'
import AvisosVigencia from '../../catalogo/components/articulos/AvisosVigencia'
import BloquePlegable from './BloquePlegable'
import styles from '../pages/CasoDetailPage.module.css'

export default function ArticulosSeleccionados({ articulos, puedeEscribir, bloqueado, valorando, errorValoracion, valorarArticulo }) {
  const ordenados = [...articulos].sort((a, b) => Number(Boolean(a.es_sugerencia)) - Number(Boolean(b.es_sugerencia)))
  const seleccionados = ordenados.filter((a) => a.valoracion === 'util')
  const pendientes = ordenados.filter((a) => !a.valoracion || a.valoracion === 'sin_valorar')
  const descartados = articulos.filter((a) => a.valoracion === 'no_util')
  const control = (a) => puedeEscribir && (
    <label className={styles.valoracion}>
      Utilidad para este caso
      <select aria-label={`Utilidad del artículo ${a.articulo?.numero_articulo} de ${a.articulo?.norma_sigla}`}
        value={a.valoracion || 'sin_valorar'} disabled={valorando != null || bloqueado}
        onChange={(e) => valorarArticulo(a.id, e.target.value)}>
        <option value="sin_valorar">Sin valorar</option>
        <option value="util">Útil</option>
        <option value="no_util">No útil</option>
      </select>
      {valorando === a.id && <span role="status">Guardando…</span>}
    </label>
  )
  const fila = (a) => (
    <li key={a.id} className={styles.listItem}>
      <div className={styles.articuloHeader}>
        <span className={styles.articuloNumero}>Art. {a.articulo?.numero_articulo} — {a.articulo?.norma_sigla}</span>
        {a.valoracion_desactualizada && <span className={`${styles.badge} ${styles.badgePending}`}>Valorado en un contexto anterior</span>}
        {a.es_sugerencia && <span className={`${styles.badge} ${styles.badgePending}`}>Recomendación complementaria</span>}
      </div>
      {a.articulo?.titulo && <p className={styles.articuloTitulo}>{a.articulo.titulo}</p>}
      {a.coincidencias?.length > 0 && <p className={styles.hintText}>Relación identificada: {a.coincidencias.join(', ')}</p>}
      {a.motivo_recomendacion && <p className={styles.hintText}>{a.motivo_recomendacion}</p>}
      {a.articulo?.avisos_vigencia?.length > 0 && (
        <details>
          <summary>Ver avisos normativos ({a.articulo.avisos_vigencia.length})</summary>
          <AvisosVigencia avisos={a.articulo.avisos_vigencia} />
        </details>
      )}
      <p className={styles.articuloContenido}><TextoVigencia texto={a.articulo?.contenido} avisos={a.articulo?.avisos_vigencia} /></p>
      {control(a)}
      {puedeEscribir && a.valoracion === 'util' && a.valoracion_desactualizada && (
        <button className={styles.btnSecondary} disabled={valorando != null || bloqueado}
          onClick={() => valorarArticulo(a.id, 'util')}>Confirmar utilidad para el contexto actual</button>
      )}
    </li>
  )
  if (!articulos.length) return null
  return (
    <>
    {errorValoracion && <div role="alert" className={styles.errorBanner}>{errorValoracion}</div>}
    <BloquePlegable titulo="Artículos seleccionados" icono="ti-book">
      <p className={styles.hintText}>Artículos marcados como útiles para revisar este caso. Esta valoración no confirma su aplicación jurídica.</p>
      {seleccionados.some((a) => a.valoracion_desactualizada) && (
        <p role="status" className={styles.hintText}>El contexto del caso cambió. Algunos artículos fueron marcados como útiles para una versión anterior y se conservan como referencia. Revisa si siguen siendo pertinentes para la descripción actual.</p>
      )}
      {!seleccionados.length && <p className={styles.hintText}>No quedan artículos seleccionados.</p>}
      <ol className={styles.list} aria-label="Artículos seleccionados">
        {seleccionados.map(fila)}
      </ol>
    </BloquePlegable>
      {descartados.length > 0 && (
        <BloquePlegable titulo={`Artículos descartados (${descartados.length})`} icono="ti-book-off" abiertoInicial={false}>
          <p className={styles.hintText}>Puedes corregir estas decisiones antes de volver a analizar.</p>
          <ul className={styles.list} aria-label="Artículos descartados">
            {descartados.map((a) => (
              <li className={styles.listItem} key={a.id}>
                <span className={styles.articuloNumero}>Art. {a.articulo?.numero_articulo} — {a.articulo?.norma_sigla}</span>
                {a.coincidencias?.length > 0 && <p className={styles.hintText}>Relación identificada: {a.coincidencias.join(', ')}</p>}
                {control(a)}
              </li>
            ))}
          </ul>
        </BloquePlegable>
      )}
    <BloquePlegable titulo="Artículos sin valorar" icono="ti-list-check">
      <p className={styles.hintText}>Revisa estos artículos. Al marcarlos como «Útil» pasarán a los seleccionados; «No útil» los enviará a descartados.</p>
      {!pendientes.length && <p className={styles.hintText}>No hay artículos pendientes de valorar.</p>}
      <ol className={styles.list} aria-label="Artículos sin valorar">{pendientes.map(fila)}</ol>
    </BloquePlegable>
    </>
  )
}
