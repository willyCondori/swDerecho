export default function NameDescriptionForm({
  mode = 'crear', styles, idPrefix, titles, icon, placeholders,
  descriptionLabel = 'Descripción (opcional)', nameFullWidth = true,
  form,
  fieldErrors = {},
  enviando,
  onChange,
  onSubmit,
  onCancel,
}) {
  const esEdicion = mode === 'editar'

  return (
    <form onSubmit={onSubmit} noValidate className={styles.formCard}>
      <h2 className={styles.cardTitle}>
        <i className={esEdicion ? 'ti ti-pencil' : icon} aria-hidden="true" />
        {esEdicion ? titles.edit : titles.create}
      </h2>

      <div className={styles.formGrid}>
        <div className={`${styles.field} ${nameFullWidth ? styles.fullWidth : ''}`}>
          <label className={styles.label} htmlFor={`${idPrefix}Nombre`}>Nombre</label>
          <input
            id={`${idPrefix}Nombre`}
            className={styles.input}
            name="nombre"
            value={form.nombre}
            onChange={onChange}
            placeholder={placeholders.name}
            disabled={enviando}
          />
          {fieldErrors.nombre && (
            <span className={styles.fieldError}>{fieldErrors.nombre}</span>
          )}
        </div>

        <div className={`${styles.field} ${styles.fullWidth}`}>
          <label className={styles.label} htmlFor={`${idPrefix}Descripcion`}>{descriptionLabel}</label>
          <textarea
            id={`${idPrefix}Descripcion`}
            className={styles.textarea}
            name="descripcion"
            value={form.descripcion}
            onChange={onChange}
            placeholder={placeholders.description}
            disabled={enviando}
          />
          {fieldErrors.descripcion && (
            <span className={styles.fieldError}>{fieldErrors.descripcion}</span>
          )}
        </div>
      </div>

      {fieldErrors.detail && (
        <div className={styles.errorBanner}>{fieldErrors.detail}</div>
      )}

      <div className={styles.submitRow}>
        <button type="button" className={styles.btnSecondary} onClick={onCancel} disabled={enviando}>
          Cancelar
        </button>
        <button type="submit" className={styles.btnPrimary} disabled={enviando}>
          {enviando ? 'Guardando...' : esEdicion ? 'Guardar cambios' : titles.submit}
        </button>
      </div>
    </form>
  )
}
