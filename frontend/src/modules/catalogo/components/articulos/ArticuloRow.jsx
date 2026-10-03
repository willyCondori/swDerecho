// modules/catalogo/components/articulos/ArticuloRow.jsx
import { getRamaKey } from '../../utils/rama'
import JerarquiaNivel from './JerarquiaNivel'
import styles from '../../pages/articulos/VerArticulos.module.css'
import { useEffect, useState } from 'react'
import catalogoApi from '../../../../api/catalogoApi'

export default function ArticuloRow({ articulo, isExpanded, onToggleExpand }) {
  const [contenidoCompleto, setContenidoCompleto] = useState(null)
  const [errorDetalle, setErrorDetalle] = useState(false)
  const [intento, setIntento] = useState(0)
  const preview = articulo.contenido_preview ?? articulo.contenido

  useEffect(() => {
    if (!isExpanded || contenidoCompleto !== null || articulo.contenido !== undefined) return
    let activo = true
    setErrorDetalle(false)
    catalogoApi.articulo(articulo.id).then(({ data }) => {
      if (activo) setContenidoCompleto(data.contenido)
    }).catch(() => {
      if (activo) setErrorDetalle(true)
    })
    return () => { activo = false }
  }, [isExpanded, articulo.id, articulo.contenido, contenidoCompleto, intento])
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
          {preview && (
            <>
              <p className={styles.contenidoPreview}>{preview}</p>
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
          <JerarquiaNivel
            nivel={jerarquiaNivel}
            nombre={jerarquiaNombre}
          />
        </td>
      </tr>

      {isExpanded && (
        <tr className={styles.expandedRow}>
          <td colSpan={5}>
            {errorDetalle ? (
              <div role="alert">
                No se pudo cargar el artículo.
                <button onClick={() => setIntento((n) => n + 1)}>Reintentar</button>
              </div>
            ) : (
              <pre className={styles.expandedContent}>
                {articulo.contenido ?? contenidoCompleto ?? 'Cargando artículo…'}
              </pre>
            )}
          </td>
        </tr>
      )}
    </>
  )
}
