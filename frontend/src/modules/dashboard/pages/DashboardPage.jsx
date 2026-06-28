// modules/dashboard/pages/DashboardPage.jsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import casosApi from '../../../api/casosApi'
import useAuthStore from '../../auth/store/authStore'
import styles from './DashboardPage.module.css'

// ── Configuración del pipeline IA ─────────────────────────
const PIPELINE_STEPS = [
  { key: 'chunking',   label: 'Chunking',         icon: 'ti-scissors' },
  { key: 'embeddings', label: 'Embeddings',        icon: 'ti-vector' },
  { key: 'ranking',    label: 'Ranking jurídico',  icon: 'ti-sort-descending' },
  { key: 'llm',        label: 'LLM (GPT4All)',     icon: 'ti-message-circle' },
]

// ── Helpers de vista ──────────────────────────────────────
function getEstadoBadge(caso) {
  if (caso.tiene_resultado) return { label: 'Completo',   cls: styles['completo'] }
  if (!caso.tiene_resultado && caso.tiene_documento) return { label: 'Analizando', cls: styles['analizando'] }
  return { label: 'Pendiente', cls: styles['pendiente'] }
}

function getBorderClass(caso) {
  if (caso.tiene_resultado)   return styles.borderGreen
  if (caso.tiene_documento)   return styles.borderPurple
  return styles.borderAmber
}

function formatFecha(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const diff = Math.floor((Date.now() - d) / 1000)
  if (diff < 3600)  return `hace ${Math.floor(diff / 60)}m`
  if (diff < 86400) return `hace ${Math.floor(diff / 3600)}h`
  return d.toLocaleDateString('es-BO', { day: 'numeric', month: 'short' })
}

function getGreeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Buenos días'
  if (h < 18) return 'Buenas tardes'
  return 'Buenas noches'
}

// ── Skeleton ──────────────────────────────────────────────
function MetricSkeleton() {
  return (
    <div className={styles.metricCard}>
      <div className={styles.metricTop}>
        <div className={`${styles.skeleton} ${styles.skeletonText}`} style={{ width: 80 }} />
        <div className={styles.skeleton} style={{ width: 30, height: 30, borderRadius: 6 }} />
      </div>
      <div className={`${styles.skeleton} ${styles.skeletonBlock}`} style={{ width: 60, height: 36 }} />
      <div className={`${styles.skeleton} ${styles.skeletonText}`} style={{ width: 100 }} />
    </div>
  )
}

// ── Componente principal ──────────────────────────────────
export default function DashboardPage() {
  const navigate              = useNavigate()
  const { user }              = useAuthStore()
  const [casos, setCasos]     = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  // Estadísticas derivadas
  const total       = casos.length
  const completos   = casos.filter((c) => c.tiene_resultado).length
  const conPdf      = casos.filter((c) => c.tiene_documento).length
  const pendientes  = total - completos

  // Top artículos simulado (en producción vendría de /api/ia/ranking/resumen/)
  const TOP_ARTICULOS = [
    { numero: 'Art. 251', titulo: 'Homicidio', count: 38, pct: 76 },
    { numero: 'Art. 331', titulo: 'Robo',      count: 29, pct: 58 },
    { numero: 'Art. 263', titulo: 'Lesiones',  count: 21, pct: 42 },
    { numero: 'Art. 335', titulo: 'Estafa',    count: 17, pct: 34 },
    { numero: 'Art. 272', titulo: 'Violencia', count: 14, pct: 28 },
  ]

  // Pipeline IA — en producción del estado Celery del último análisis
  const pipelineState = {
    chunking:   'done',
    embeddings: 'done',
    ranking:    'active',
    llm:        'waiting',
  }

  const pipelineWidth = {
    done:    '100%',
    active:  '55%',
    waiting: '0%',
  }

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const { data } = await casosApi.misCasos({ page_size: 20 })
        setCasos(data.results ?? data)
      } catch (e) {
        setError('No se pudieron cargar los casos.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const casoRecientes = casos.slice(0, 5)

  return (
    <div className={styles.root}>
      {/* ── Encabezado ───────────────────────────────── */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <p className={styles.greeting}>{getGreeting()}, sistema activo</p>
          <h1 className={styles.title}>Panel de control</h1>
          <p className={styles.subtitle}>
            {new Date().toLocaleDateString('es-BO', {
              weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
            })}
          </p>
        </div>
        <div className={styles.headerActions}>
          <button
            className={styles.btnSecondary}
            onClick={() => navigate('/casos')}
          >
            <i className="ti ti-folder" aria-hidden="true" />
            Ver casos
          </button>
          <button
            className={styles.btnPrimary}
            onClick={() => navigate('/casos/nuevo')}
          >
            <i className="ti ti-plus" aria-hidden="true" />
            Nuevo caso
          </button>
        </div>
      </header>

      {/* ── Métricas ─────────────────────────────────── */}
      <section aria-label="Resumen de métricas">
        <div className={styles.metricsGrid}>
          {loading ? (
            [1, 2, 3, 4].map((k) => <MetricSkeleton key={k} />)
          ) : (
            <>
              <div className={styles.metricCard}>
                <div className={styles.metricTop}>
                  <span className={styles.metricLabel}>Casos activos</span>
                  <span className={`${styles.metricIcon} ${styles.purple}`}>
                    <i className="ti ti-folder" aria-hidden="true" />
                  </span>
                </div>
                <span className={styles.metricValue}>{total}</span>
                <span className={`${styles.metricDelta} ${styles.up}`}>
                  <i className="ti ti-arrow-up" aria-hidden="true" />
                  {completos} completados
                </span>
              </div>

              <div className={styles.metricCard}>
                <div className={styles.metricTop}>
                  <span className={styles.metricLabel}>Análisis IA</span>
                  <span className={`${styles.metricIcon} ${styles.green}`}>
                    <i className="ti ti-cpu" aria-hidden="true" />
                  </span>
                </div>
                <span className={styles.metricValue}>{completos}</span>
                <span className={`${styles.metricDelta} ${styles.neutral}`}>
                  procesados con GPT4All
                </span>
              </div>

              <div className={styles.metricCard}>
                <div className={styles.metricTop}>
                  <span className={styles.metricLabel}>Con PDF</span>
                  <span className={`${styles.metricIcon} ${styles.amber}`}>
                    <i className="ti ti-file-text" aria-hidden="true" />
                  </span>
                </div>
                <span className={styles.metricValue}>{conPdf}</span>
                <span className={`${styles.metricDelta} ${styles.neutral}`}>
                  documentos subidos
                </span>
              </div>

              <div className={styles.metricCard}>
                <div className={styles.metricTop}>
                  <span className={styles.metricLabel}>Pendientes</span>
                  <span className={`${styles.metricIcon} ${styles.blue}`}>
                    <i className="ti ti-clock" aria-hidden="true" />
                  </span>
                </div>
                <span className={styles.metricValue}>{pendientes}</span>
                <span className={`${styles.metricDelta} ${pendientes > 0 ? styles.down : styles.neutral}`}>
                  {pendientes > 0 ? 'requieren análisis' : 'todo al día'}
                </span>
              </div>
            </>
          )}
        </div>
      </section>

      {/* ── Cuerpo principal ─────────────────────────── */}
      <div className={styles.mainGrid}>
        {/* Columna izquierda */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>

          {/* Casos recientes */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <h2 className={styles.cardTitle}>
                <i className={`ti ti-folder ${styles.cardTitleIcon}`} aria-hidden="true" />
                Casos recientes
              </h2>
              <button className={styles.cardLink} onClick={() => navigate('/casos')}>
                Ver todos →
              </button>
            </div>

            {loading ? (
              <div className={styles.caseList}>
                {[1, 2, 3].map((k) => (
                  <div key={k} className={`${styles.skeleton} ${styles.skeletonBlock}`} style={{ height: 58 }} />
                ))}
              </div>
            ) : error ? (
              <div className={styles.emptyState}>
                <i className={`ti ti-wifi-off ${styles.emptyIcon}`} aria-hidden="true" />
                <p className={styles.emptyText}>{error}</p>
                <button className={styles.btnSecondary} onClick={() => window.location.reload()}>
                  Reintentar
                </button>
              </div>
            ) : casoRecientes.length === 0 ? (
              <div className={styles.emptyState}>
                <i className={`ti ti-folder-off ${styles.emptyIcon}`} aria-hidden="true" />
                <p className={styles.emptyText}>Sin casos registrados aún.</p>
                <button className={styles.btnPrimary} onClick={() => navigate('/casos/nuevo')}>
                  <i className="ti ti-plus" aria-hidden="true" /> Crear primer caso
                </button>
              </div>
            ) : (
              <div className={styles.caseList}>
                {casoRecientes.map((caso) => {
                  const estado = getEstadoBadge(caso)
                  return (
                    <div
                      key={caso.id}
                      className={`${styles.caseItem} ${getBorderClass(caso)}`}
                      onClick={() => navigate(`/casos/${caso.id}`)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => e.key === 'Enter' && navigate(`/casos/${caso.id}`)}
                      aria-label={`Ver caso ${caso.codigo}`}
                    >
                      <div className={styles.caseItemLeft}>
                        <span className={styles.caseCodigo}>{caso.codigo} · {caso.titulo}</span>
                        <span className={styles.caseInfo}>
                          {caso.cliente_nombre} · {formatFecha(caso.created_at)}
                        </span>
                      </div>
                      <span className={`${styles.badge} ${estado.cls}`}>
                        {estado.label}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Artículos más usados */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <h2 className={styles.cardTitle}>
                <i className={`ti ti-award ${styles.cardTitleIcon}`} aria-hidden="true" />
                Artículos más aplicados
              </h2>
              <button className={styles.cardLink} onClick={() => navigate('/catalogo')}>
                Ver catálogo →
              </button>
            </div>
            <div className={styles.articuloList}>
              {TOP_ARTICULOS.map((art) => (
                <div key={art.numero} className={styles.articuloItem}>
                  <div className={styles.articuloBody}>
                    <div className={styles.articuloHeader}>
                      <span className={styles.articuloNombre}>{art.numero} — {art.titulo}</span>
                      <span className={styles.articuloCount}>{art.count}</span>
                    </div>
                    <div className={styles.articuloBarBg}>
                      <div className={styles.articuloBar} style={{ width: `${art.pct}%` }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Columna derecha */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>

          {/* Pipeline IA */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <h2 className={styles.cardTitle}>
                <i className={`ti ti-cpu ${styles.cardTitleIcon}`} aria-hidden="true" />
                Pipeline IA
              </h2>
              <button className={styles.cardLink} onClick={() => navigate('/ia')}>
                Detalles →
              </button>
            </div>
            <div className={styles.pipelineList}>
              {PIPELINE_STEPS.map((step) => {
                const state = pipelineState[step.key]
                return (
                  <div key={step.key} className={styles.pipelineStep}>
                    <div className={`${styles.pipelineIcon} ${styles[state]}`}>
                      <i className={`ti ${step.icon}`} aria-hidden="true" />
                    </div>
                    <div className={styles.pipelineBody}>
                      <div className={styles.pipelineLabel}>
                        <span className={styles.pipelineStepName}>{step.label}</span>
                        <span className={`${styles.pipelineStatus} ${styles[state]}`}>
                          {state === 'done' ? 'OK' : state === 'active' ? 'En proceso' : 'Esperando'}
                        </span>
                      </div>
                      <div className={styles.pipelineBar}>
                        <div
                          className={`${styles.pipelineProgress} ${styles[state]}`}
                          style={{ width: pipelineWidth[state] }}
                        />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Acceso rápido */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <h2 className={styles.cardTitle}>
                <i className={`ti ti-bolt ${styles.cardTitleIcon}`} aria-hidden="true" />
                Acceso rápido
              </h2>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
              {[
                { icon: 'ti-folder-plus', label: 'Nuevo caso',           path: '/casos/nuevo' },
                { icon: 'ti-user-plus',   label: 'Nuevo cliente',        path: '/clientes/nuevo' },
                { icon: 'ti-upload',      label: 'Subir plantilla',      path: '/plantillas' },
                { icon: 'ti-chart-bar',   label: 'Ver ranking IA',       path: '/ia' },
              ].map((item) => (
                <button
                  key={item.path}
                  className={styles.btnSecondary}
                  style={{ justifyContent: 'flex-start', width: '100%' }}
                  onClick={() => navigate(item.path)}
                >
                  <i className={`ti ${item.icon}`} aria-hidden="true" />
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
