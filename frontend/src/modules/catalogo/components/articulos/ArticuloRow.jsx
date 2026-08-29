// modules/catalogo/components/articulos/ArticuloRow.jsx
import { getRamaKey } from '../../utils/rama'
import JerarquiaBar from './JerarquiaBar'
import styles from '../../pages/articulos/VerArticulos.module.css'

export default function ArticuloRow({ articulo, isExpanded, onToggleExpand }) {
  const ramaNombre = articulo.rama?.nombre || articulo.rama_nombre || '—'
  const normaObj = articulo.norma || {}
  const normaNombre = normaObj.nombre || articulo.norma_nombre || '—'
  const normaSigla = normaObj.sigla || articulo.norma_sigla || ''

  // El endpoint de listado (ArticuloListSerializer) devuelve
  // jerarquia_nivel/jerarquia_nombre planos; el de detalle
  // (ArticuloReadSerializer) devuelve norma.jerarquia anidado.
  // Se soportan ambos formatos.
  const jerarquiaNivel = normaObj.jerarquia?.nivel ?? articulo.jerarquia_nivel ?? null
  const jerarquiaNombre = normaObj.jerarquia?.nombre ?? articulo.jerarquia_nombre ?? null

  return (
    <>
      <tr className={styles.tr}>
        <td className={styles.td}>
          <div className={styles.numCell}>
            <span className={styles.numPill}>Art. {articulo.numero_articulo}</span>
          </div>
        </td>

        <td className={`${styles.td} ${styles.tituloCell}`}>
          {articulo.titulo ? (
            <p className={styles.tituloText} title={articulo.titulo}>{articulo.titulo}</p>
          ) : (
            <p className={styles.noTitulo}>Sin título</p>
          )}
          {articulo.contenido && (
            <>
              <p className={styles.contenidoPreview}>{articulo.contenido}</p>
              <button
                className={styles.expandBtn}
                onClick={() => onToggleExpand(articulo.id)}
                aria-expanded={isExpanded}
              >
                {isExpanded ? '▲ Ocultar' : '▼ Ver completo'}
              </button>
            </>
          )}
        </td>

        <td className={styles.td}>
          <span className={`${styles.ramaBadge} ${styles[getRamaKey(ramaNombre)]}`}>
            <i className="ti ti-git-branch" aria-hidden="true" />
            {ramaNombre}
          </span>
        </td>

        <td className={styles.td}>
          <div className={styles.normaCell}>
            <span className={styles.normaName} title={normaNombre}>{normaNombre}</span>
            {normaSigla && <span className={styles.normaSigla}>{normaSigla}</span>}
          </div>
        </td>

        <td className={`${styles.td} ${styles.jerarquiaCell}`}>
          <JerarquiaBar
            nivel={jerarquiaNivel}
            nombre={jerarquiaNombre}
          />
        </td>
      </tr>

      {isExpanded && (
        <tr className={styles.expandedRow}>
          <td colSpan={5}>
            <pre className={styles.expandedContent}>{articulo.contenido}</pre>
          </td>
        </tr>
      )}
    </>
  )
}