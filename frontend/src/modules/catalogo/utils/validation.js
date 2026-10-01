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
 *
 * modo: 'nueva' (por defecto) exige nombreDocumento + jerarquiaId, igual
 * que antes. modo 'existente' exige en cambio normaId (elegido de una
 * lista) y no le pide nombre ni jerarquía al usuario, porque la norma
 * elegida ya los tiene.
 *
 * @param {{archivo: File|null, modo?: 'nueva'|'existente', normaId?: string, nombreDocumento: string, sigla: string, jerarquiaId: string, ramaId: string}} datos
 * @returns {Record<string, string>} mapa de errores por campo (vacío si todo es válido).
 */
export function validarFormulario({ archivo, modo = 'nueva', normaId, nombreDocumento, sigla, jerarquiaId, ramaId }) {
  const errores = {}

  if (!archivo) errores.archivo = 'Debes seleccionar un archivo PDF.'

  if (modo === 'existente') {
    if (!normaId) errores.normaId = 'Selecciona la norma a la que corresponde este PDF.'
  } else {
    if (!nombreDocumento || !nombreDocumento.trim()) {
      errores.nombreDocumento = 'Escribe el nombre del documento.'
    } else if (nombreDocumento.trim().length < 3) {
      errores.nombreDocumento = 'El nombre debe tener al menos 3 caracteres.'
    }
    // La sigla es opcional (ej. "CPP", "CPE"); el backend la usa para
    // reutilizar la norma si ya existe, igual que el nombre.
    if (sigla && sigla.trim().length > 50) {
      errores.sigla = 'La sigla no puede superar los 50 caracteres.'
    }
    if (!jerarquiaId) errores.jerarquiaId = 'Selecciona el tipo de norma (jerarquía).'
  }

  if (!ramaId) errores.ramaId = 'Selecciona la rama de derecho.'

  return errores
}