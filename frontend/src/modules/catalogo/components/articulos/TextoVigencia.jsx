import TextoResaltado from './TextoResaltado'

export default function TextoVigencia({ texto = '', avisos = [], busqueda = '' }) {
  const rangos = []
  for (const aviso of avisos) {
    if (aviso.operacion !== 'deroga' || aviso.estado !== 'confirmado' || aviso.parte_afectada?.tipo !== 'parcial') continue
    for (const parte of aviso.parte_afectada.partes || []) {
      const fragmento = parte.fragmento
      if (!fragmento) continue
      const inicio = texto.indexOf(fragmento)
      if (inicio < 0 || texto.indexOf(fragmento, inicio + 1) >= 0) continue
      rangos.push({ inicio, fin: inicio + fragmento.length, descripcion: parte.descripcion })
    }
  }
  if (!rangos.length) return <TextoResaltado texto={texto} busqueda={busqueda} />
  rangos.sort((a, b) => a.inicio - b.inicio)
  const salida = []; let finAnterior = 0
  for (const rango of rangos) {
    if (rango.inicio < finAnterior) continue
    salida.push(<TextoResaltado key={`t-${rango.inicio}`} texto={texto.slice(finAnterior, rango.inicio)} busqueda={busqueda} />)
    salida.push(<mark key={`d-${rango.inicio}`} title={`Parte derogada: ${rango.descripcion}`} aria-label={`Parte derogada: ${rango.descripcion}`}>
      <TextoResaltado texto={texto.slice(rango.inicio, rango.fin)} busqueda={busqueda} />
    </mark>)
    finAnterior = rango.fin
  }
  salida.push(<TextoResaltado key="final" texto={texto.slice(finAnterior)} busqueda={busqueda} />)
  return <>{salida}</>
}
