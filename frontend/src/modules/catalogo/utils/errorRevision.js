const CAMPOS = {
  archivo: 'Archivo PDF', norma_id: 'Norma existente', nombre_documento: 'Nombre del documento',
  rama_id: 'Rama de derecho', jerarquia_id: 'Tipo de norma', motor_lectura: 'Lectura del documento',
  metadatos: 'Datos de la norma', identidades_secciones: 'Normas de los anexos',
  variantes_secciones: 'Alternativas de los anexos', variantes_unidades: 'Alternativas de artículos',
}

export function mensajeErrorRevision(error) {
  const datos = error.response?.data
  const mensajes = []
  const visitar = (valor, campo = '') => {
    if (typeof valor === 'string' && valor.trim()) {
      mensajes.push(campo ? `${campo}: ${valor}` : valor)
    } else if (Array.isArray(valor)) valor.forEach((v) => visitar(v, campo))
    else if (valor && typeof valor === 'object') Object.entries(valor).forEach(([k, v]) => {
      const etiqueta = ['detail', 'non_field_errors'].includes(k) ? campo : (CAMPOS[k] || k)
      visitar(v, campo && etiqueta !== campo ? `${campo} / ${etiqueta}` : etiqueta)
    })
  }
  visitar(datos)
  if (mensajes.length) return [...new Set(mensajes)].join('\n')
  if (error.response?.status === 400) return 'El servidor rechazó la revisión del PDF sin indicar el motivo. Revisa el archivo y los datos de la norma.'
  return error.message || 'No se pudo revisar el PDF.'
}
