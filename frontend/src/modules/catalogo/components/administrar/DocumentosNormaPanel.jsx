// modules/catalogo/components/administrar/DocumentosNormaPanel.jsx
import useDocumentosNorma from '../../hooks/useDocumentosNorma'
import useAuthStore from '../../../auth/store/authStore'
import { formatFechaHora } from '../../../casos/utils/etapas'
import { formatTamano } from '../../../documentos/utils/descargas'
import baseStyles from '../../pages/AdministrarCatalogoPage.module.css'
import styles from './DocumentosNormaPanel.module.css'

// Panel embebido bajo NormaTable: lista los PDF que se subieron para
// extraer los artículos de una norma puntual (GET
// /api/catalogo/documentos-norma/por_norma/). Se abre desde el botón
// "Documentos" de cada fila; no reemplaza el formulario de carga, solo
// deja ver/descargar/eliminar lo que ya se subió.
export default function DocumentosNormaPanel({ norma, onClose }) {
  const isAdmin = useAuthStore((s) => s.isAdmin())
  const {
    documentos, loading, error,
    eliminandoId, descargandoId,
    descargarDocumento, eliminarDocumento,
  } = useDocumentosNorma(norma.id)

  const handleEliminar = async (documento) => {
    const confirmado = window.confirm(
      `¿Eliminar "${documento.nombre_original}"? No afecta a los artículos ya extraídos de "${norma.nombre}", solo borra este PDF fuente.`
    )
    if (!confirmado) return
    await eliminarDocumento(documento.id)
  }

  return (
    <div className={baseStyles.card}>
      <div className={baseStyles.sectionToolbar}>
        <h3 className={baseStyles.itemNombre}>
          <i className="ti ti-folder" aria-hidden="true" /> Documentos de “{norma.nombre}”
        </h3>
        <button type="button" className={baseStyles.iconBtn} title="Cerrar" onClick={onClose}>
          <i className="ti ti-x" aria-hidden="true" />
        </button>
      </div>

      {error && <div className={baseStyles.errorBanner}>{error}</div>}

      {loading ? (
        <p className={baseStyles.emptyText}>Cargando documentos...</p>
      ) : documentos.length === 0 ? (
        <p className={baseStyles.emptyText}>
          Esta norma todavía no tiene ningún PDF cargado.
        </p>
      ) : (
        <ul className={styles.list}>
          {documentos.map((doc) => (
            <li key={doc.id} className={styles.item}>
              <i className={`ti ti-file-type-pdf ${styles.itemIcon}`} aria-hidden="true" />
              <div className={styles.itemInfo}>
                <span className={baseStyles.itemNombre}>{doc.nombre_original}</span>
                <span className={baseStyles.itemDescripcion}>
                  {formatTamano(doc.tamano)} · {doc.rama_nombre || 'sin rama'} ·{' '}
                  {formatFechaHora(doc.created_at)}
                  {doc.subido_por_nombre ? ` · subido por ${doc.subido_por_nombre}` : ''}
                </span>
              </div>
              <button
                type="button"
                className={baseStyles.iconBtn}
                onClick={() => descargarDocumento(doc)}
                disabled={descargandoId === doc.id}
                title="Descargar"
              >
                <i className="ti ti-download" aria-hidden="true" />
              </button>
              {isAdmin && (
                <button
                  type="button"
                  className={baseStyles.iconBtn}
                  onClick={() => handleEliminar(doc)}
                  disabled={eliminandoId === doc.id}
                  title="Eliminar"
                >
                  <i className="ti ti-trash" aria-hidden="true" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
