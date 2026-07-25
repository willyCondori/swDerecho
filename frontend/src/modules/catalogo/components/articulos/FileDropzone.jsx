// modules/catalogo/components/articulos/FileDropzone.jsx
import { formatBytes } from '../../utils/format'
import { MAX_SIZE_MB } from '../../utils/validation'
import styles from '../../pages/articulos/CargaArticulosPage.module.css'

export default function FileDropzone({
  archivo,
  dragOver,
  error,
  fileInputRef,
  onFileChange,
  onAbrirSelector,
  onDragOver,
  onDragLeave,
  onDrop,
  onRemover,
}) {
  return (
    <>
      <div
        className={`${styles.dropzone} ${dragOver ? styles.dragOver : ''} ${archivo ? styles.hasFile : ''}`}
        onClick={() => !archivo && onAbrirSelector()}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        role="button"
        tabIndex={0}
        aria-label="Seleccionar archivo PDF"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf,.pdf"
          className={styles.fileInput}
          onChange={(e) => onFileChange(e.target.files?.[0])}
        />

        {!archivo ? (
          <>
            <div className={styles.dropzoneIcon}>
              <i className="ti ti-cloud-upload" aria-hidden="true" />
            </div>
            <p className={styles.dropzoneText}>
              <strong>Haz clic para subir</strong> o arrastra el archivo aquí
            </p>
            <p className={styles.dropzoneHint}>
              Solo PDF · Máximo {MAX_SIZE_MB} MB
            </p>
          </>
        ) : (
          <div className={styles.filePreview}>
            <div className={styles.fileIconBox}>
              <i className="ti ti-file-type-pdf" aria-hidden="true" />
            </div>
            <div className={styles.fileInfo}>
              <p className={styles.fileName}>{archivo.name}</p>
              <p className={styles.fileSize}>{formatBytes(archivo.size)}</p>
            </div>
            <button
              type="button"
              className={styles.fileRemove}
              onClick={(e) => { e.stopPropagation(); onRemover() }}
              aria-label="Quitar archivo"
            >
              <i className="ti ti-x" aria-hidden="true" />
            </button>
          </div>
        )}
      </div>

      {error && (
        <span className={styles.fieldError}>
          <i className="ti ti-alert-circle" aria-hidden="true" />
          {error}
        </span>
      )}
    </>
  )
}