// modules/casos/pages/NuevoCasoPage.jsx
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useCrearCaso from '../hooks/useCrearCaso'
import catalogoApi from '../../../api/catalogoApi'
import clientesApi from '../../../api/clientesApi'
import styles from './NuevoCasoPage.module.css'

function BuscadorCliente({ clienteExistenteId, clienteExistenteNombre, onSeleccionar, error }) {
  const [query, setQuery] = useState('')
  const [resultados, setResultados] = useState([])
  const [buscando, setBuscando] = useState(false)
  const [mostrarLista, setMostrarLista] = useState(false)

  useEffect(() => {
    if (query.trim().length < 2) {
      setResultados([])
      return
    }
    const timeoutId = setTimeout(() => {
      setBuscando(true)
      clientesApi.buscar(query.trim())
        .then(({ data }) => setResultados(data))
        .catch((e) => console.error('Error buscando clientes:', e))
        .finally(() => setBuscando(false))
    }, 350)
    return () => clearTimeout(timeoutId)
  }, [query])

  if (clienteExistenteId) {
    return (
      <div className={styles.field}>
        <label className={styles.label}>Cliente seleccionado</label>
        <div className={styles.clienteSeleccionado}>
          <span>{clienteExistenteNombre}</span>
          <button type="button" className={styles.btnLink} onClick={() => onSeleccionar(null, '')}>
            Cambiar
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.field} style={{ position: 'relative' }}>
      <label className={styles.label}>Buscar cliente</label>
      <input
        className={styles.input}
        value={query}
        onChange={(e) => { setQuery(e.target.value); setMostrarLista(true) }}
        onFocus={() => setMostrarLista(true)}
        placeholder="Escribe al menos 2 letras del nombre..."
      />
      {error && <span className={styles.fieldError}>{error}</span>}

      {mostrarLista && query.trim().length >= 2 && (
        <div className={styles.dropdownResultados}>
          {buscando && <div className={styles.dropdownItem}>Buscando...</div>}
          {!buscando && resultados.length === 0 && (
            <div className={styles.dropdownItem}>Sin resultados.</div>
          )}
          {!buscando && resultados.map((c) => (
            <div
              key={c.id}
              className={styles.dropdownItem}
              onClick={() => {
                onSeleccionar(c.id, c.nombre_completo)
                setMostrarLista(false)
                setQuery('')
              }}
            >
              {c.nombre_completo}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function NuevoCasoPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)
  const [ramas, setRamas] = useState([])
  const {
    form, clienteForm, modo, archivo, fieldErrors, enviando, error,
    modoCliente, clienteExistenteId, clienteExistenteNombre,
    onChange, onArchivoChange, cambiarModo, cambiarModoCliente,
    seleccionarClienteExistente, onSubmit,
  } = useCrearCaso()

  useEffect(() => {
    catalogoApi.listaRamas()
      .then(({ data }) => setRamas(data))
      .catch((e) => console.error('Error cargando ramas:', e))
  }, [])

  return (
    <div className={styles.root}>
      <div className={styles.headerRow}>
        <button type="button" className={styles.backBtn} onClick={() => navigate('/casos')} aria-label="Volver">
          <i className="ti ti-arrow-left" aria-hidden="true" />
        </button>
        <div>
          <h1 className={styles.title}>Nuevo caso</h1>
          <p className={styles.subtitle}>Registra al cliente y describe el caso con texto o un PDF.</p>
        </div>
      </div>

      {error && <div className={styles.errorBanner}>{error}</div>}

      <form onSubmit={onSubmit} noValidate>
        <div className={styles.card}>

          <h2 className={styles.cardTitle}>
            <i className="ti ti-user-plus" aria-hidden="true" /> Datos del cliente
          </h2>

          <div className={styles.tabs}>
            <button
              type="button"
              className={`${styles.tab} ${modoCliente === 'nuevo' ? styles.tabActive : ''}`}
              onClick={() => cambiarModoCliente('nuevo')}
            >
              <i className="ti ti-user-plus" aria-hidden="true" /> Cliente nuevo
            </button>
            <button
              type="button"
              className={`${styles.tab} ${modoCliente === 'existente' ? styles.tabActive : ''}`}
              onClick={() => cambiarModoCliente('existente')}
            >
              <i className="ti ti-users" aria-hidden="true" /> Cliente existente
            </button>
          </div>

          {modoCliente === 'nuevo' ? (
            <div className={styles.formGrid}>
              <div className={styles.field}>
                <label className={styles.label}>Nombres</label>
                <input className={styles.input} name="nombres" value={clienteForm.nombres} onChange={onChange} placeholder="Nombres" />
                {fieldErrors.nombres && <span className={styles.fieldError}>{fieldErrors.nombres}</span>}
              </div>

              <div className={styles.field}>
                <label className={styles.label}>Apellidos</label>
                <input className={styles.input} name="apellidos" value={clienteForm.apellidos} onChange={onChange} placeholder="Apellidos" />
                {fieldErrors.apellidos && <span className={styles.fieldError}>{fieldErrors.apellidos}</span>}
              </div>

              <div className={styles.field}>
                <label className={styles.label}>Teléfono</label>
                <input
                  className={styles.input}
                  type="text"
                  name="telefono"
                  value={clienteForm.telefono}
                  onChange={(e) => {
                    const soloNumeros = e.target.value.replace(/[^0-9]/g, '')
                    onChange({ target: { name: 'telefono', value: soloNumeros.slice(0, 8) } })
                  }}
                  placeholder="7########"
                />
                {fieldErrors.telefono && <span className={styles.fieldError}>{fieldErrors.telefono}</span>}
              </div>
            </div>
          ) : (
            <div className={styles.formGrid}>
              <div className={`${styles.field} ${styles.fullWidth}`}>
                <BuscadorCliente
                  clienteExistenteId={clienteExistenteId}
                  clienteExistenteNombre={clienteExistenteNombre}
                  onSeleccionar={seleccionarClienteExistente}
                  error={fieldErrors.clienteExistente}
                />
              </div>
            </div>
          )}

          <h2 className={styles.cardTitle} style={{ marginTop: 'var(--sp-4)' }}>
            <i className="ti ti-briefcase" aria-hidden="true" /> Datos del caso
          </h2>

          <div className={styles.tabs}>
            <button
              type="button"
              className={`${styles.tab} ${modo === 'texto' ? styles.tabActive : ''}`}
              onClick={() => cambiarModo('texto')}
            >
              <i className="ti ti-align-left" aria-hidden="true" /> Texto
            </button>
            <button
              type="button"
              className={`${styles.tab} ${modo === 'pdf' ? styles.tabActive : ''}`}
              onClick={() => cambiarModo('pdf')}
            >
              <i className="ti ti-file-text" aria-hidden="true" /> PDF
            </button>
          </div>

          <div className={styles.formGrid}>
            <div className={`${styles.field} ${styles.fullWidth}`}>
              <label className={styles.label}>Título del caso</label>
              <input
                className={styles.input}
                name="titulo"
                value={form.titulo}
                onChange={onChange}
                placeholder="Ej. Demanda por incumplimiento de contrato"
              />
              {fieldErrors.titulo && <span className={styles.fieldError}>{fieldErrors.titulo}</span>}
            </div>

            <div className={`${styles.field} ${styles.fullWidth}`}>
              <label className={styles.label}>Rama del derecho</label>
              <select
                className={styles.input}
                name="rama_id"
                value={form.rama_id || ''}
                onChange={onChange}
              >
                <option value="">Detectar automáticamente</option>
                {ramas.map((r) => (
                  <option key={r.id} value={r.id}>{r.nombre}</option>
                ))}
              </select>
              {fieldErrors.rama_id && <span className={styles.fieldError}>{fieldErrors.rama_id}</span>}
            </div>

            {modo === 'texto' ? (
              <div className={`${styles.field} ${styles.fullWidth}`}>
                <label className={styles.label}>Descripción del caso</label>
                <textarea
                  className={styles.textarea}
                  name="descripcion"
                  value={form.descripcion}
                  onChange={onChange}
                  placeholder="Describe los hechos, antecedentes y lo que buscas resolver..."
                />
                {fieldErrors.descripcion && <span className={styles.fieldError}>{fieldErrors.descripcion}</span>}
              </div>
            ) : (
              <div className={`${styles.field} ${styles.fullWidth}`}>
                <label className={styles.label}>Archivo PDF</label>
                <div
                  className={styles.dropzone}
                  onClick={() => fileInputRef.current?.click()}
                  role="button"
                  tabIndex={0}
                >
                  <i className={`ti ti-cloud-upload ${styles.dropzoneIcon}`} aria-hidden="true" />
                  {archivo ? (
                    <span className={styles.fileName}>
                      <i className="ti ti-file-text" aria-hidden="true" /> {archivo.name}
                    </span>
                  ) : (
                    <span>Haz clic para seleccionar un PDF</span>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf"
                  style={{ display: 'none' }}
                  onChange={(e) => onArchivoChange(e.target.files?.[0] ?? null)}
                />
                {fieldErrors.archivo && <span className={styles.fieldError}>{fieldErrors.archivo}</span>}

                <label className={styles.label} style={{ marginTop: 'var(--sp-3)' }}>
                  Notas adicionales (opcional)
                </label>
                <textarea
                  className={styles.textarea}
                  style={{ minHeight: 80 }}
                  name="descripcion"
                  value={form.descripcion}
                  onChange={onChange}
                  placeholder="Contexto adicional para el análisis..."
                />
              </div>
            )}
          </div>

          <div className={styles.submitRow}>
            <button type="button" className={styles.btnSecondary} onClick={() => navigate('/casos')} disabled={enviando}>
              Cancelar
            </button>
            <button type="submit" className={styles.btnPrimary} disabled={enviando}>
              {enviando ? 'Creando...' : 'Crear caso'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}