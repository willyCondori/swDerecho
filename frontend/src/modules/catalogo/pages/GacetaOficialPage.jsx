import { useNavigate } from 'react-router-dom'
import catalogoApi from '../../../api/catalogoApi'
import GacetaPanel from '../components/articulos/GacetaPanel'
import { useBorradorCarga } from '../hooks/useBorradorCarga'
import { useRevisionPdf } from '../hooks/useRevisionPdf'
import { FORM_INICIAL } from '../utils/formCargaInicial'
import styles from './articulos/CargaArticulosPage.module.css'

export default function GacetaOficialPage() {
  const navigate = useNavigate()
  const { actualizar } = useBorradorCarga(FORM_INICIAL)
  const { revisando, limpiarRevision } = useRevisionPdf()
  const elegirOficial = async (documento, archivo) => {
    if (revisando) throw new Error('Hay una revisión de PDF en curso. Espera a que termine antes de elegir otro documento.')
    const [ramas, jerarquias] = await Promise.all([catalogoApi.ramas(), catalogoApi.jerarquias()])
    actualizar((b) => ({ archivo, modo: 'articulos', seleccion: [], revisionSeleccion: null,
      form: { ...FORM_INICIAL, motorLectura: b.form.motorLectura || FORM_INICIAL.motorLectura,
        nombreDocumento: documento.titulo, tipoNorma: documento.tipo, numeroNorma: documento.numero || '',
        fechaPublicacion: documento.fecha_publicacion || '', urlFuente: documento.url_fuente,
        documentoOficialId: documento.id,
        ramaId: ramas.data.find((r) => /penal/i.test(r.nombre))?.id || '',
        jerarquiaId: jerarquias.data.find((j) => j.nombre.toLowerCase() === documento.tipo.toLowerCase())?.id || '',
      } }))
    limpiarRevision()
    navigate('/catalogo/cargar')
  }
  return <div className={styles.root}><GacetaPanel onElegir={elegirOficial} /></div>
}
