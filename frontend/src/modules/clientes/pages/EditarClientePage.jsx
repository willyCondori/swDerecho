// modules/clientes/pages/EditarClientePage.jsx
import { useNavigate, useParams } from 'react-router-dom'
import useEditarCliente from '../hooks/useEditarCliente'
import ClienteForm from '../components/ClienteForm'
import styles from './ClientesPage.module.css'

function getNombreCompleto(cliente) {
  if (!cliente) return ''
  const nombres = cliente.nombres ?? ''
  const apellidos = cliente.apellidos ?? ''
  return `${nombres} ${apellidos}`.trim() || `Cliente #${cliente.id}`
}

export default function EditarClientePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const {
    cliente, form, fieldErrors, cargando, error, enviando, guardadoOk, onChange, onSubmit, reload,
  } = useEditarCliente(id)

  return (
    <div className={styles.root}>
      <div className={styles.headerRow}>
        <button
          type="button"
          className={styles.backBtn}
          onClick={() => navigate('/clientes')}
          aria-label="Volver"
        >
          <i className="ti ti-arrow-left" aria-hidden="true" />
        </button>
        <div>
          <h1 className={styles.title}>Editar cliente</h1>
          <p className={styles.subtitle}>
            {cargando ? 'Cargando...' : getNombreCompleto(cliente)}
          </p>
        </div>
      </div>

      {cargando ? (
        <div className={styles.card}>Cargando cliente...</div>
      ) : error && !cliente ? (
        <div className={styles.card}>
          <p className={styles.fieldError}>{error}</p>
          <button type="button" className={styles.btnPrimary} onClick={reload}>
            Reintentar
          </button>
        </div>
      ) : (
        <>
          {error && <div className={styles.errorBanner}>{error}</div>}
          {guardadoOk && (
            <div className={styles.errorBanner} style={{ background: 'var(--c-success-bg, #e6f7ee)', color: 'var(--c-success-text, #1a7f4b)' }}>
              <i className="ti ti-check" aria-hidden="true" /> Cambios guardados correctamente.
            </div>
          )}
          <ClienteForm
            form={form}
            fieldErrors={fieldErrors}
            enviando={enviando}
            onChange={onChange}
            onSubmit={onSubmit}
            submitLabel={enviando ? 'Guardando...' : 'Guardar cambios'}
          />
        </>
      )}
    </div>
  )
}
