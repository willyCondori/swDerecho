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
    <div className={styles.root}>
      <div className={styles.headerRow}>
        <button
          type="button"
          className={styles.backBtn}
          onClick={() => navigate('/usuarios')}
          aria-label="Volver"
        >
          <i className="ti ti-arrow-left" aria-hidden="true" />
        </button>
        <div>
          <h1 className={styles.title}>Editar usuario</h1>
          <p className={styles.subtitle}>
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
            <div className={styles.successBox}>
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
