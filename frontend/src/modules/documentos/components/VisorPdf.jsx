import { lazy, Suspense } from 'react'
import Modal from '../../../components/ui/Modal'

const Contenido = lazy(() => import('./VisorPdfContenido'))

export default function VisorPdf(props) {
  return <Suspense fallback={<Modal open onClose={props.onClose} title={props.nombre || 'Documento PDF'} description="Preparando lector…" />}>
    <Contenido {...props} />
  </Suspense>
}
