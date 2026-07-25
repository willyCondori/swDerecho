// modules/casos/pages/CasoDetailPage.jsx
import { useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import useCasoDetail from '../hooks/useCasoDetail'
import styles from './CasoDetailPage.module.css'

function EstadoBadge({ tieneResultado, tieneDocumento }) {
  if (tieneResultado) {
    return <span className={`${styles.badge} ${styles.badgeOk}`}>Análisis completo</span>
  }
  if (tieneDocumento) {
    return <span className={`${styles.badge} ${styles.badgePending}`}>PDF adjunto, sin analizar</span>
  }
  return <span className={`${styles.badge} ${styles.badgeMuted}`}>Sin analizar</span>
}

export default function CasoDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const fileInputRef = useRef(null)
  const [analisisEncolado, setAnalisisEncolado] = useState(false)

  const {
    caso, articulos, loading, error,
    analizando, subiendoPdf, analizar, subirPdf, reload,
  } = useCasoDetail(id)

  if (loading) {
    return <div className={styles.loaderWrap}>Cargando caso...</div>
  }

  if (error && !caso) {
    return (
      <div className={styles.root}>
        <div className={styles.errorBanner}>{error}</div>
        <button className={styles.btnSecondary} onClick={() => navigate('/casos')}>
          Volver a casos
        </button>
      </div>
    )
  }

  if (!caso) return null

  const handleAnalizar = async () => {
    const ok = await analizar()
    if (ok) setAnalisisEncolado(false)
        await reload()  // recarga el caso para reflejar el estado de análisis encolado
  }

  const handleArchivoSeleccionado = async (e) => {
    const file = e.target.files?.[0]
    if (file) await subirPdf(file)
  }

  return (
    <div className={styles.root}>
      <div className={styles.headerRow}>
        <button type="button" className={styles.backBtn} onClick={() => navigate('/casos')} aria-label="Volver">
          <i className="ti ti-arrow-left" aria-hidden="true" />
        </button>
        <div className={styles.headerInfo}>
          <div className={styles.codigoRow}>
            <span className={styles.codigo}>{caso.codigo}</span>
            <EstadoBadge tieneResultado={caso.tiene_generado || !!caso.resultado} tieneDocumento={caso.tiene_documento} />
          </div>
          <h1 className={styles.title}>{caso.titulo}</h1>
        </div>
      </div>

      {error && <div className={styles.errorBanner}>{error}</div>}

      <div className={styles.grid}>
        {/* Columna principal */}
        <div className={styles.mainCol}>

          <div className={styles.card}>
            <h2 className={styles.cardTitle}>
              <i className="ti ti-file-description" aria-hidden="true" /> Descripción del caso
            </h2>
            {caso.descripcion ? (
              <p className={styles.descripcion}>{caso.descripcion}</p>
            ) : (
              <p className={styles.emptyText}>Este caso no tiene descripción de texto (se envió como PDF).</p>
            )}

            <div className={styles.pdfRow}>
              {caso.tiene_documento ? (
                <span className={styles.pdfBadge}>
                  <i className="ti ti-file-text" aria-hidden="true" /> PDF adjunto
                </span>
              ) : (
                <span className={styles.emptyText}>Sin PDF adjunto.</span>
              )}
              <button
                type="button"
                className={styles.btnLink}
                onClick={() => fileInputRef.current?.click()}
                disabled={subiendoPdf}
              >
                {subiendoPdf ? 'Subiendo...' : caso.tiene_documento ? 'Reemplazar PDF' : 'Adjuntar PDF'}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                style={{ display: 'none' }}
                onChange={handleArchivoSeleccionado}
              />
            </div>
          </div>

          {caso.hechos?.length > 0 && (
            <div className={styles.card}>
              <h2 className={styles.cardTitle}>
                <i className="ti ti-list-details" aria-hidden="true" /> Hechos
              </h2>
              <ol className={styles.list}>
                {caso.hechos.map((h) => (
                  <li key={h.id} className={styles.listItem}>{h.descripcion}</li>
                ))}
              </ol>
            </div>
          )}

          {caso.petitorios?.length > 0 && (
            <div className={styles.card}>
              <h2 className={styles.cardTitle}>
                <i className="ti ti-gavel" aria-hidden="true" /> Petitorios
              </h2>
              <ol className={styles.list}>
                {caso.petitorios.map((p) => (
                  <li key={p.id} className={styles.listItem}>{p.descripcion}</li>
                ))}
              </ol>
            </div>
          )}

          {caso.resultado && (
            <div className={styles.card}>
              <h2 className={styles.cardTitle}>
                <i className="ti ti-sparkles" aria-hidden="true" /> Resultado del análisis IA
              </h2>

              {caso.resultado.resumen && (
                <div className={styles.resultBlock}>
                  <h3 className={styles.resultLabel}>Resumen</h3>
                  <p className={styles.descripcion}>{caso.resultado.resumen}</p>
                </div>
              )}
              {caso.resultado.fortalezas && (
                <div className={styles.resultBlock}>
                  <h3 className={styles.resultLabel}>Fortalezas</h3>
                  <p className={styles.descripcion}>{caso.resultado.fortalezas}</p>
                </div>
              )}
              {caso.resultado.debilidades && (
                <div className={styles.resultBlock}>
                  <h3 className={styles.resultLabel}>Debilidades</h3>
                  <p className={styles.descripcion}>{caso.resultado.debilidades}</p>
                </div>
              )}
              {caso.resultado.estrategias && (
                <div className={styles.resultBlock}>
                  <h3 className={styles.resultLabel}>Estrategias</h3>
                  <p className={styles.descripcion}>{caso.resultado.estrategias}</p>
                </div>
              )}
            </div>
          )}

        {articulos.length > 0 && (
          <div className={styles.card}>
            <h2 className={styles.cardTitle}>
              <i className="ti ti-book" aria-hidden="true" /> Artículos aplicables
            </h2>
            <ol className={styles.list}>
              {articulos.map((a) => (
                <li key={a.id} className={styles.listItem}>
                  <div className={styles.articuloHeader}>
                    <span className={styles.articuloNumero}>
                      Art. {a.articulo?.numero_articulo} — {a.articulo?.norma_sigla}
                    </span>
                    <span className={styles.articuloScore}>
                      {Math.round((a.score_total ?? 0) * 100)}% relevancia
                    </span>
                  </div>
                  {a.articulo?.titulo && (
                    <p className={styles.articuloTitulo}>{a.articulo.titulo}</p>
                  )}
                  <p className={styles.articuloContenido}>{a.articulo?.contenido}</p>
                </li>
              ))}
            </ol>
          </div>
        )}
        </div>

        {/* Columna lateral */}
        <div className={styles.sideCol}>
          <div className={styles.card}>
            <h2 className={styles.cardTitle}>
              <i className="ti ti-user" aria-hidden="true" /> Cliente
            </h2>
            <p className={styles.sideText}>
              {caso.cliente?.nombre_completo || `Cliente #${caso.cliente?.id ?? '—'}`}
            </p>
          </div>

          <div className={styles.card}>
            <h2 className={styles.cardTitle}>
              <i className="ti ti-user-check" aria-hidden="true" /> Abogado a cargo
            </h2>
            <p className={styles.sideText}>
              {caso.usuario?.nombre_completo || caso.usuario?.usuario || '—'}
            </p>
          </div>

          {caso.rama_detectada && (
            <div className={styles.card}>
              <h2 className={styles.cardTitle}>
                <i className="ti ti-category" aria-hidden="true" /> Rama del derecho
              </h2>
              <p className={styles.sideText}>{caso.rama_detectada}</p>
            </div>
          )}

          <div className={styles.card}>
            <button
              type="button"
              className={styles.btnPrimary}
              onClick={handleAnalizar}
              disabled={analizando || analisisEncolado}
            >
              {analizando
                ? 'Encolando análisis...'
                : analisisEncolado
                  ? 'Análisis en proceso...'
                  : caso.resultado
                    ? 'Volver a analizar'
                    : 'Analizar caso con IA'}
            </button>
            {analisisEncolado && (
              <p className={styles.hintText}>
                El análisis corre en segundo plano. Recargá la página en unos minutos para ver el resultado.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}