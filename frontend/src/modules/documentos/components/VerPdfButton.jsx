import { useState } from 'react'
import VisorPdf from './VisorPdf'

export default function VerPdfButton({ documentoId, nombre, origen = 'norma', className }) {
  const [abierto, setAbierto] = useState(false)
  return <>
    <button type="button" className={className} title="Ver PDF" aria-label={`Ver PDF ${nombre}`} onClick={() => setAbierto(true)}>Ver PDF</button>
    {abierto && <VisorPdf documentoId={documentoId} nombre={nombre} origen={origen} onClose={() => setAbierto(false)} />}
  </>
}
