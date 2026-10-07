import CatalogoEntityTable from './CatalogoEntityTable'
import styles from '../../pages/AdministrarCatalogoPage.module.css'

export default function EntidadTable({ entidades, busqueda, onCrearPrimero, ...props }) {
  const empty = busqueda?.trim() ? { icon: 'ti-search', text: `No se encontraron entidades para “${busqueda.trim()}”.` } : { icon: 'ti-users', text: 'Todavía no hay entidades jurídicas registradas.',
    action: <button type="button" className={styles.btnPrimary} onClick={onCrearPrimero}>
      <i className="ti ti-plus" aria-hidden="true" /> Nueva entidad</button> }
  return <CatalogoEntityTable {...props} rows={entidades} recoverLabel="Recuperar entidad" empty={empty} />
}
