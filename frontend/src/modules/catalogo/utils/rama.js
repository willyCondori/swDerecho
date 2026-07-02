// modules/catalogo/utils/rama.js

/**
 * Determina la clave de estilo (color) según el nombre de la rama.
 * El componente que consuma esto debe mapear la clave a su CSS module:
 * styles[getRamaKey(nombre)]
 */
export function getRamaKey(nombre = '') {
  const n = nombre.toLowerCase()
  if (n.includes('penal')) return 'penal'
  if (n.includes('civil')) return 'civil'
  if (n.includes('laboral')) return 'laboral'
  if (n.includes('constit') || n.includes('cpe')) return 'cpe'
  return 'default'
}