// modules/catalogo/components/articulos/CargasEnCursoAviso.jsx
import styles from '../../pages/articulos/CargaArticulosPage.module.css'

// Cargas de PDF que otros usuarios tienen corriendo en este momento.
export default function CargasEnCursoAviso({ cargas }) {
  if (!cargas?.length) return null

  return (
    <div className={styles.enCursoBox} role="status" aria-live="polite">
      <p className={styles.enCursoTitle}>
        <i className={`ti ti-loader-2 ${styles.spinningInline}`} aria-hidden="true" />{' '}
        {cargas.length === 1 ? 'Hay una carga en curso' : `Hay ${cargas.length} cargas en curso`}
      </p>
      <ul className={styles.enCursoList}>
        {cargas.map((c) => (
          <li key={c.task_id} className={styles.enCursoItem}>
            <span>
              <strong>{c.nombre_documento || c.archivo || 'Documento'}</strong>
              {c.usuario_nombre ? ` — iniciada por ${c.usuario_nombre}` : ''}
            </span>
            <span className={styles.enCursoPaso}>
              {c.progreso ?? 0}%{c.paso ? ` · ${c.paso}` : ''}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
