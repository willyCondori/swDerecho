import NameDescriptionForm from '../../../components/ui/NameDescriptionForm'
import styles from '../pages/RolesPage.module.css'

export default function RolForm(props) {
  return <NameDescriptionForm {...props} styles={styles} idPrefix="rol" icon="ti ti-shield-plus"
    titles={{ edit: 'Editar rol', create: 'Nuevo rol', submit: 'Crear rol' }}
    placeholders={{ name: 'Ej: Recepcionista', description: 'Para qué se usa este rol y qué nivel de acceso otorga...' }} descriptionLabel="Descripción" nameFullWidth={false} />
}
