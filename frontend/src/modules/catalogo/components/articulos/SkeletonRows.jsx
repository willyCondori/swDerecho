// modules/catalogo/components/articulos/SkeletonRows.jsx
import styles from '../../pages/articulos/VerArticulos.module.css'

export default function SkeletonRows({ cols, rows = 8 }) {
  return Array.from({ length: rows }).map((_, i) => (
    <tr key={i} className={styles.tr}>
      {Array.from({ length: cols }).map((__, j) => (
        <td key={j} className={styles.td}>
          <span
            className={styles.skeleton}
            style={{ width: `${50 + Math.random() * 40}%` }}
          />
        </td>
      ))}
    </tr>
  ))
}