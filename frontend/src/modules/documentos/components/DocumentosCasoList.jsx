// modules/documentos/components/DocumentosCasoList.jsx
import { useRef, useState } from 'react'
import useDocumentosCaso from '../hooks/useDocumentosCaso'
import useAuthStore from '../../auth/store/authStore'
import { formatFechaHora } from '../../casos/utils/etapas'
import styles from './DocumentosCasoList.module.css'

const EXTENSIONES_ACEPTADAS = '.pdf,.doc,.docx,.txt'

function formatTamano(bytes) {
  if (!bytes && bytes !== 0) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function iconoPorExtension(tipoArchivo) {
  const ext = (tipoArchivo || '').toLowerCase()
  if (ext === 'pdf') return 'ti-file-type-pdf'
  if (ext === 'doc' || ext === 'docx') return 'ti-file-type-doc'
  return 'ti-file-text'
}

// Lista los documentos asociados a un caso (GET /api/documentos/por_caso/),
// con subida, descarga y eliminación. Vive dentro de CasoDetailPage, junto
// a la ficha del caso — no reemplaza el flujo de "PDF principal del caso"
// que ya maneja useCasoDetail, sino que cubre documentos adicionales
// (respaldos, contratos, pruebas, etc.).
export default function DocumentosCasoList({ casoId }) {
  const fileInputRef = useRef(null)
  const puedeEscribir = useAuthStore((s) => s.puedeEscribir())
  const isAdmin = useAuthStore((s) => s.isAdmin())
  const [errorEliminar, setErrorEliminar] = useState('')

  const {
    documentos, tipos, loading, error, subiendo,
    eliminandoId, descargandoId,
    subirDocumento, descargarDocumento, eliminarDocumento,
  } = useDocumentosCaso(casoId)

  const handleSeleccionarArchivo = () => {
    if (!tipos.length) return
    fileInputRef.current?.click()
  }

  const handleArchivoElegido = async (e) => {
    const archivo = e.target.files?.[0]
    e.target.value = '' // permite volver a elegir el mismo archivo después
    if (!archivo || !tipos.length) return
    // El tipo por defecto es "caso_pdf" si existe (el que usa el flujo
    // de alta de caso); si no, se usa el primero del catálogo.
    const tipoPorDefecto = tipos.find((t) => t.tipo === 'caso_pdf') || tipos[0]
    await subirDocumento(archivo, tipoPorDefecto.id)
  }

  const handleEliminar = async (documento) => {
    const confirmado = window.confirm(
      `¿Eliminar "${documento.nombre_original}"? Esta acción no se puede deshacer.`
    )
    if (!confirmado) return
    setErrorEliminar('')
    const res = await eliminarDocumento(documento.id)
    if (!res.ok) setErrorEliminar(res.error)
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.headerRow}>
        <h3 className={styles.subtitle}>
          <i className="ti ti-folder" aria-hidden="true" /> Documentos del caso
        </h3>
        {puedeEscribir && (
          <>
            <button
              type="button"
              className={styles.btnLink}
              onClick={handleSeleccionarArchivo}
              disabled={subiendo || !tipos.length}
              title={!tipos.length ? 'No hay tipos de documento configurados' : undefined}
            >
              <i className="ti ti-upload" aria-hidden="true" />{' '}
              {subiendo ? 'Subiendo...' : 'Subir documento'}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept={EXTENSIONES_ACEPTADAS}
              style={{ display: 'none' }}
              onChange={handleArchivoElegido}
            />
          </>
        )}
      </div>

      {(error || errorEliminar) && (
        <div className={styles.errorBanner}>{error || errorEliminar}</div>
      )}

      {loading ? (
        <p className={styles.emptyText}>Cargando documentos...</p>
      ) : documentos.length === 0 ? (
        <p className={styles.emptyText}>Todavía no hay documentos adicionales en este caso.</p>
      ) : (
        <ul className={styles.list}>
          {documentos.map((doc) => (
            <li key={doc.id} className={styles.item}>
              <i className={`ti ${iconoPorExtension(doc.tipo_archivo)} ${styles.itemIcon}`} aria-hidden="true" />
              <div className={styles.itemInfo}>
                <span className={styles.itemNombre}>{doc.nombre_original}</span>
                <span className={styles.itemMeta}>
                  {formatTamano(doc.tamano)} · {formatFechaHora(doc.created_at)}
                </span>
              </div>
              <div className={styles.itemAcciones}>
                <button
                  type="button"
                  className={styles.iconBtn}
                  onClick={() => descargarDocumento(doc)}
                  disabled={descargandoId === doc.id}
                  aria-label={`Descargar ${doc.nombre_original}`}
                  title="Descargar"
                >
                  <i className="ti ti-download" aria-hidden="true" />
                </button>
                {isAdmin && (
                  <button
                    type="button"
                    className={`${styles.iconBtn} ${styles.iconBtnDanger}`}
                    onClick={() => handleEliminar(doc)}
                    disabled={eliminandoId === doc.id}
                    aria-label={`Eliminar ${doc.nombre_original}`}
                    title="Eliminar"
                  >
                    <i className="ti ti-trash" aria-hidden="true" />
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
