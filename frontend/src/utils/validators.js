// frontend/src/utils/validators.js
//
// Saneamiento de texto compartido por los formularios de la app.
// Se usa tanto en el onChange (filtrado en tiempo real mientras el
// usuario escribe) como en el validate() de cada formulario (para
// cubrir el caso de que un valor inválido llegue por otra vía, ej.
// autocompletado del navegador).

// ── Solo letras/espacios (nombres, apellidos) ──────────────────────
// Deja pasar letras (con tildes/ñ) y espacios; descarta números,
// símbolos y emojis. Además colapsa 3+ espacios seguidos a un máximo
// de 2, para que no se puedan pegar/tipear cadenas de espacios.
export function soloLetrasEspacios(value) {
  return value
    .replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '')
    .replace(/ {3,}/g, '  ')
}

// ── Texto libre (títulos, descripciones, nombres de catálogo) ─────
// Acá sí se permiten números y puntuación, pero igual se bloquean
// emojis y más de 2 espacios seguidos.
const EMOJI_REGEX =
  /[\u{1F1E6}-\u{1F1FF}\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{2190}-\u{21FF}\u{2B00}-\u{2BFF}\u{FE0F}\u{200D}]/gu

export function sinEmojis(value) {
  return value.replace(EMOJI_REGEX, '')
}

export function limitarEspacios(value) {
  return value.replace(/ {3,}/g, '  ')
}

export function sanearTextoLibre(value) {
  return limitarEspacios(sinEmojis(value))
}

// ── Validaciones (para usar dentro de validate(), como defensa
// adicional al filtrado en tiempo real) ────────────────────────────
export function tieneEspaciosExcesivos(value) {
  return /\s{3,}/.test(value)
}

export function tieneEmoji(value) {
  return EMOJI_REGEX.test(value)
}
