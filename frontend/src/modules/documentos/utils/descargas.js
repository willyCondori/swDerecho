// modules/documentos/utils/descargas.js
// Dispara la descarga de un blob ya recibido del backend (axios con
// responseType: 'blob'), sin necesidad de exponer una URL pública del
// archivo. Se reutiliza en useDocumentosCaso, usePlantillas y
// useDocumentosGenerados para no repetir el mismo boilerplate de
// createObjectURL / <a> temporal / revokeObjectURL.
export function descargarBlob(blob, nombreArchivo) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = nombreArchivo || 'documento'
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export function formatTamano(bytes) {
  if (!bytes && bytes !== 0) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function iconoPorExtension(tipoArchivo) {
  const ext = (tipoArchivo || '').toLowerCase()
  if (ext === 'pdf') return 'ti-file-type-pdf'
  if (ext === 'doc' || ext === 'docx' || ext === 'dotx') return 'ti-file-type-doc'
  return 'ti-file-text'
}
