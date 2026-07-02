// modules/catalogo/utils/format.js

/**
 * Formatea un tamaño en bytes a una representación legible (B, KB, MB).
 */
export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}