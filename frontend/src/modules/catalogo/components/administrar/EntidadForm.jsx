import NameDescriptionForm from '../../../../components/ui/NameDescriptionForm'
import styles from '../../pages/AdministrarCatalogoPage.module.css'
import { sanearTextoLibre } from '../../../../utils/validators'

export default function EntidadForm({ onChange, ...props }) {
  return <NameDescriptionForm {...props} styles={styles} idPrefix="entidad" icon="ti ti-users"
    titles={{ edit: 'Editar entidad jurídica', create: 'Nueva entidad jurídica', submit: 'Crear entidad' }}
    placeholders={{ name: 'Ej: Menor de edad, Funcionario público', description: 'En qué casos aplica esta entidad y cómo afecta el análisis...' }} onChange={(event) => onChange({ target: { name: event.target.name, value: sanearTextoLibre(event.target.value) } })} />
}
