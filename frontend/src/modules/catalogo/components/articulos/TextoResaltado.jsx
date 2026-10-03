export default function TextoResaltado({ texto = '', busqueda = '' }) {
  const terminos = [...new Set(busqueda.trim().split(/\s+/).filter(Boolean))]
  if (!terminos.length) return texto
  const patron = new RegExp(`(${terminos.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi')
  return texto.split(patron).map((parte, i) => i % 2 ? <mark key={i}>{parte}</mark> : parte)
}
