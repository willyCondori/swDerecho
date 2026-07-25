// modules/usuarios/pages/EditarUsuarioPage.jsx
import { useNavigate, useParams } from 'react-router-dom'
import useEditarUsuario from '../hooks/useEditarUsuario'
import UsuarioForm from '../components/UsuarioForm'
import styles from './UsuarioForm.module.css'

export default function EditarUsuarioPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const {
    usuario,
    form,
    fieldErrors,
    cargando,
    error,
    enviando,
    guardadoOk,
    onChange,
    onSubmit,
    reload,
  } = useEditarUsuario(id)

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)', marginBottom: 'var(--sp-4)' }}>
        <button
          type="button"
          onClick={() => navigate('/usuarios')}
          aria-label="Volver"
          style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '1.2rem' }}
        >
          <i className="ti ti-arrow-left" aria-hidden="true" />
        </button>
        <div>
          <h1 style={{ margin: 0 }}>Editar usuario</h1>
          <p style={{ margin: 0, color: 'var(--text-secondary, #6b7280)' }}>
            {cargando ? 'Cargando...' : (usuario?.usuario ?? `#${id}`)}
          </p>
        </div>
      </div>

      {cargando ? (
        <div className={styles.card}>Cargando usuario...</div>
      ) : error ? (
        <div className={styles.card}>
          <p className={styles.fieldError}>{error}</p>
          <button type="button" className={styles.btnPrimary} onClick={reload}>
            Reintentar
          </button>
        </div>
      ) : (
        <>
          {guardadoOk && (
            <div className={styles.card} style={{ marginBottom: 'var(--sp-3)', color: '#16a34a' }}>
              <i className="ti ti-check" aria-hidden="true" /> Cambios guardados correctamente.
            </div>
          )}
          <UsuarioForm
            mode="editar"
            usuario={usuario}
            form={form}
            fieldErrors={fieldErrors}
            enviando={enviando}
            onChange={onChange}
            onSubmit={onSubmit}
          />
        </>
      )}
    </div>
  )
}