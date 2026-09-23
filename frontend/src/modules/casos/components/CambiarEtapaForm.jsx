// modules/casos/components/CambiarEtapaForm.jsx
import { useEffect, useState } from 'react'
import { sanearTextoLibre } from '../../../utils/validators'
import styles from './Seguimiento.module.css'

const NOTA_MAX = 2000

// Solo se monta para quienes pueden escribir (administrador y abogado).
// `onSubmit(etapa, nota)` debe devolver { ok, error? }.
export default function CambiarEtapaForm({ etapas, etapaActual, guardando, onSubmit }) {
  const [etapa, setEtapa] = useState(etapaActual)
  const [nota, setNota] = useState('')
  const [error, setError] = useState('')

  // Si la etapa cambia por fuera (recarga del caso), el selector la sigue.
  useEffect(() => {
    setEtapa(etapaActual)
  }, [etapaActual])

  const mismaEtapa = etapa === etapaActual

  const handleSubmit = async (e) => {
    e.preventDefault()
    const notaLimpia = nota.trim()

    if (mismaEtapa && !notaLimpia) {
      setError('Elige otra etapa o escribe una nota para registrar el seguimiento.')
      return
    }

    setError('')
    const resultado = await onSubmit(etapa, notaLimpia)
    if (resultado.ok) {
      setNota('')
    } else {
      setError(resultado.error)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="etapa-caso">Etapa</label>
        <select
          id="etapa-caso"
          className={styles.select}
          value={etapa}
          onChange={(e) => setEtapa(e.target.value)}
          disabled={guardando || etapas.length === 0}
        >
          {etapas.map((et) => (
            <option key={et.value} value={et.value}>{et.label}</option>
          ))}
        </select>
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="nota-seguimiento">
          Nota de seguimiento {mismaEtapa ? '' : '(opcional)'}
        </label>
        <textarea
          id="nota-seguimiento"
          className={styles.textarea}
          value={nota}
          maxLength={NOTA_MAX}
          onChange={(e) => setNota(sanearTextoLibre(e.target.value))}
          placeholder="Ej. Se presentó la denuncia; audiencia fijada para el 25 de septiembre"
          disabled={guardando}
        />
        <span className={styles.contador}>{nota.length}/{NOTA_MAX}</span>
      </div>

      {error && <span className={styles.fieldError} role="alert">{error}</span>}

      <button
        type="submit"
        className={`${styles.btnPrimary} ${styles.submit}`}
<<<<<<< HEAD
        disabled={guardando || etapas.length === 0}
=======
        disabled={guardando || opciones.length === 0 || !etapa}
>>>>>>> 643e3e225dba5ab29e1278da6bd213a00a3abb20
      >
        {guardando ? 'Guardando...' : mismaEtapa ? 'Agregar nota' : 'Cambiar etapa'}
      </button>
    </form>
  )
}
