import styles from './Normativa.module.css'

function diferencias(antes, despues) {
  let inicio = 0
  while (inicio < antes.length && inicio < despues.length && antes[inicio] === despues[inicio]) inicio++
  let finAntes = antes.length, finDespues = despues.length
  while (finAntes > inicio && finDespues > inicio && antes[finAntes - 1] === despues[finDespues - 1]) { finAntes--; finDespues-- }
  return { retirado: finAntes > inicio ? [{ inicio, fin: finAntes }] : [], agregado: finDespues > inicio ? [{ inicio, fin: finDespues }] : [] }
}

function rangosDePartes(texto, parte) {
  const rangos = []
  for (const p of parte?.partes || []) {
    if (!p.fragmento) continue
    const inicio = texto.indexOf(p.fragmento)
    if (inicio >= 0 && texto.indexOf(p.fragmento, inicio + 1) < 0) rangos.push({ inicio, fin: inicio + p.fragmento.length })
  }
  return rangos.sort((a, b) => a.inicio - b.inicio)
}

function TextoComparado({ texto, rangos, recuperar = false }) {
  const salida = []; let fin = 0
  for (const r of rangos) {
    if (r.inicio < fin) continue
    salida.push(texto.slice(fin, r.inicio))
    salida.push(recuperar
      ? <ins className={styles.textoAgregado} key={r.inicio} title="Texto a recuperar o incorporado">{texto.slice(r.inicio, r.fin)}</ins>
      : <del className={styles.textoRetirado} key={r.inicio} title="Texto retirado">{texto.slice(r.inicio, r.fin)}</del>)
    fin = r.fin
  }
  salida.push(texto.slice(fin))
  return <pre>{salida}</pre>
}

export default function ComparacionCambioArticulo({ registro: h, restaurar = false }) {
  const antes = h.texto_antes || '', despues = h.texto_despues || ''
  const modificado = antes !== despues
  const parcial = h.parte_afectada?.tipo === 'parcial'
  const diferencia = diferencias(antes, despues)
  const partes = rangosDePartes(antes, h.parte_afectada)
  const retirados = partes.length ? partes : diferencia.retirado
  const tipo = h.operacion === 'abroga' ? 'Abrogación' : parcial ? 'Derogación parcial' : 'Derogación total'
  const estado = h.aplicado === false ? `${tipo} programada` : `${tipo} confirmada`
  const recuperaTexto = restaurar && modificado && h.aplicado !== false
  return <div>
    <p className={styles.cambioResumen}>
      {modificado
        ? recuperaTexto ? `Se recuperaría la parte retirada: ${h.parte_afectada?.descripcion || 'fragmento del artículo'}.`
          : `Cambio en el texto: ${h.parte_afectada?.descripcion || 'fragmento del artículo'} ${h.aplicado === false ? 'se retirará al entrar en vigencia' : 'retirado'}.`
        : `${restaurar ? 'Se revertiría' : 'Cambio registrado'}: ${tipo.toLowerCase()}. El contenido se conserva, cambió su estado de vigencia en el sistema.`}
    </p>
    {modificado && <p>Rojo y tachado: texto retirado. Verde y subrayado: texto incorporado o que se recuperaría.</p>}
    <div className={styles.comparacionHistorial}>
      <section aria-label={restaurar ? 'Texto después del cambio original' : 'Texto antes del cambio'}>
        <h4>{restaurar ? 'Después del cambio original' : 'Antes'}</h4>
        <p className={restaurar ? styles.estadoCambio : styles.estadoAnterior}>{restaurar ? estado : 'Sin esta confirmación registrada'}</p>
        <TextoComparado texto={restaurar ? despues : antes} rangos={modificado ? restaurar ? diferencia.agregado : retirados : []} recuperar={restaurar} />
      </section>
      <section aria-label={restaurar ? 'Texto anterior a recuperar' : 'Texto después del cambio'}>
        <h4>{restaurar ? 'Texto anterior a recuperar' : h.aplicado === false ? 'Después previsto' : 'Después'}</h4>
        <p className={restaurar ? styles.estadoRecuperado : styles.estadoCambio}>{restaurar ? 'Esta confirmación se revertiría' : estado}</p>
        <TextoComparado texto={restaurar ? antes : despues} rangos={modificado ? restaurar ? retirados : diferencia.agregado : []} recuperar />
        {!modificado && <p>El cambio está en la vigencia, no en el texto reproducido.</p>}
      </section>
    </div>
    {h.estado_revision === 'revertido' && <p>Esta comparación documenta el cambio original; la confirmación ya fue revertida.</p>}
  </div>
}
