import NameDescriptionForm from '../../../../components/ui/NameDescriptionForm'
import styles from '../../pages/AdministrarCatalogoPage.module.css'
import { sanearTextoLibre } from '../../../../utils/validators'

export default function RamaForm({ onChange, ...props }) {
  return <NameDescriptionForm {...props} styles={styles} idPrefix="rama" icon="ti ti-gavel"
    titles={{ edit: 'Editar rama de derecho', create: 'Nueva rama de derecho', submit: 'Crear rama' }}
    placeholders={{ name: 'Ej: Derecho Procesal Penal', description: 'Qué tipo de casos y normas cubre esta rama...' }} onChange={(event) => onChange({ target: { name: event.target.name, value: sanearTextoLibre(event.target.value) } })} />
}
