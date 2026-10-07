import CatalogoEntityTable from './CatalogoEntityTable'
import styles from '../../pages/AdministrarCatalogoPage.module.css'

export default function RamaTable({ ramas, onCrearPrimero, ...props }) {
  const empty = { icon: 'ti-gavel', text: 'Todavía no hay ramas de derecho registradas.',
    action: <button type="button" className={styles.btnPrimary} onClick={onCrearPrimero}>
      <i className="ti ti-plus" aria-hidden="true" /> Nueva rama</button> }
  return <CatalogoEntityTable {...props} rows={ramas} recoverLabel="Recuperar rama" empty={empty} />
}
