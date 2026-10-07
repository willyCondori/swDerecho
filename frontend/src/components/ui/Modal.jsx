import * as Dialog from '@radix-ui/react-dialog'
import styles from './Modal.module.css'

export default function Modal({ open, onClose, title, description, children, busy = false }) {
  return <Dialog.Root open={open} onOpenChange={(value) => { if (!value && !busy) onClose() }}>
    <Dialog.Portal><Dialog.Overlay className={styles.overlay} />
      <Dialog.Content className={styles.content} onPointerDownOutside={(event) => event.preventDefault()}>
        <div className={styles.header}>
          <Dialog.Title className={styles.title}>{title}</Dialog.Title>
          <Dialog.Close disabled={busy} className={styles.close} aria-label="Cerrar ventana">×</Dialog.Close>
        </div>
        <Dialog.Description className={styles.description}>{description}</Dialog.Description>
        {children}
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>
}
