// modules/catalogo/utils/validation.js

export const MAX_SIZE_MB = 50

/**
 * Valida un archivo PDF individual.
 * @returns {string|null} mensaje de error, o null si es válido.
 */
export function validarArchivo(file) {
  if (!file) return null

  if (!file.name.toLowerCase().endsWith('.pdf')) {
    return 'Solo se aceptan archivos PDF (.pdf).'
  }

  const sizeMb = file.size / (1024 * 1024)
  if (sizeMb > MAX_SIZE_MB) {
    return `El archivo supera el máximo de ${MAX_SIZE_MB} MB (${sizeMb.toFixed(1)} MB).`
  }

  return null
}

/**
 * Valida los campos del formulario de carga de artículos.
 * @param {{archivo: File|null, fuente: string, normaId: string, ramaId: string}} datos
 * @returns {Record<string, string>} mapa de errores por campo (vacío si todo es válido).
 */
export function validarFormulario({ archivo, fuente, normaId, ramaId }) {
  const errores = {}

  if (!archivo) errores.archivo = 'Debes seleccionar un archivo PDF.'
  if (!fuente) errores.fuente = 'Selecciona el tipo de norma.'
  if (!normaId) errores.normaId = 'Selecciona la norma destino.'
  if (!ramaId) errores.ramaId = 'Selecciona la rama de derecho.'

  return errores
}