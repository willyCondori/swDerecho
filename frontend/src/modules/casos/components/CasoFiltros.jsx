// modules/casos/components/CasoFiltros.jsx
import { useEffect, useState } from 'react'
import clientesApi from '../../../api/clientesApi'
import styles from '../pages/CasosPage.module.css'

export default function CasoFiltros({ filtros, onChange, onLimpiar, visible }) {
  const [clientes, setClientes] = useState([])

  useEffect(() => {
    if (!visible) return
    clientesApi.listaCompacta()
      .then(({ data }) => setClientes(data ?? []))
      .catch(() => setClientes([]))
  }, [visible])

  if (!visible) return null

  const handleField = (name) => (e) => onChange({ [name]: e.target.value })

  return (
    <div className={styles.filtrosPanel}>
      <div className={styles.field}>
        <label className={styles.label}>Cliente</label>
        <select className={styles.select} value={filtros.cliente_id} onChange={handleField('cliente_id')}>
          <option value="">Todos</option>
          {clientes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nombre_completo || `${c.nombres ?? ''} ${c.apellidos ?? ''}`.trim() || `Cliente #${c.id}`}
            </option>
          ))}
        </select>
      </div>

      {/* TODO: reemplazar por <select> cuando exista un endpoint de ramas jurídicas */}
      <div className={styles.field}>
        <label className={styles.label}>Rama (ID)</label>
        <input
          className={styles.input}
          type="number"
          value={filtros.rama_id}
          onChange={handleField('rama_id')}
          placeholder="Ej. 3"
        />
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Desde</label>
        <input className={styles.input} type="date" value={filtros.fecha_desde} onChange={handleField('fecha_desde')} />
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Hasta</label>
        <input className={styles.input} type="date" value={filtros.fecha_hasta} onChange={handleField('fecha_hasta')} />
      </div>

      <div className={styles.field}>
        <label className={styles.label}>PDF</label>
        <select className={styles.select} value={filtros.tiene_pdf} onChange={handleField('tiene_pdf')}>
          <option value="">Todos</option>
          <option value="true">Con PDF</option>
          <option value="false">Sin PDF</option>
        </select>
      </div>

      <div className={styles.filtrosActions}>
        <button type="button" className={styles.btnSecondary} onClick={onLimpiar}>
          Limpiar filtros
        </button>
      </div>
    </div>
  )
}