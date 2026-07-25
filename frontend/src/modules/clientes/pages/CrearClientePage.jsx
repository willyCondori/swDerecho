// modules/clientes/pages/CrearClientePage.jsx
import { useNavigate } from 'react-router-dom'
import useCrearCliente from '../hooks/useCrearCliente'
import ClienteForm from '../components/ClienteForm'
import styles from './ClientesPage.module.css'

export default function CrearClientePage() {
  const navigate = useNavigate()
  const { form, fieldErrors, enviando, error, onChange, onSubmit } = useCrearCliente()

  return (
    <div className={styles.root}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)', marginBottom: 'var(--sp-2)' }}>
        <button
          type="button"
          onClick={() => navigate('/clientes')}
          aria-label="Volver"
          style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '1.2rem' }}
        >
          <i className="ti ti-arrow-left" aria-hidden="true" />
        </button>
        <div>
          <h1 className={styles.title} style={{ fontSize: '1.5rem' }}>Nuevo cliente</h1>
          <p className={styles.subtitle}>Registra los datos de contacto del cliente.</p>
        </div>
      </div>

      {error && <div className={styles.errorBanner}>{error}</div>}

      <ClienteForm
        form={form}
        fieldErrors={fieldErrors}
        enviando={enviando}
        onChange={onChange}
        onSubmit={onSubmit}
        submitLabel="Crear cliente"
      />
    </div>
  )
}