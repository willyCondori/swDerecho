import { useSyncExternalStore } from 'react'
import Modal from './Modal'
import { dialogStore } from './dialogs'
import styles from './Modal.module.css'
import shared from '../../styles/shared.module.css'

export default function DialogHost() {
  const current = useSyncExternalStore(dialogStore.subscribe, dialogStore.snapshot, () => null)
  if (!current) return null
  const confirm = current.kind === 'confirm'
  return <Modal open onClose={() => dialogStore.close(false)}
    title={current.title || (confirm ? 'Confirmar acción' : 'Aviso del sistema')}
    description={String(current.message)}>
    <div className={styles.actions}>
      {confirm && <button type="button" className={shared.btnSecondary} onClick={() => dialogStore.close(false)}>
        {current.cancelLabel || 'Cancelar'}</button>}
      <button type="button" className={shared.btnPrimary} onClick={() => dialogStore.close(true)}>
        {current.confirmLabel || (confirm ? 'Confirmar' : 'Entendido')}</button>
    </div>
  </Modal>
}
