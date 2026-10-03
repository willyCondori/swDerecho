import { useEffect, useState } from 'react'
import api from '../../../../api/axiosInstance'
import AvisosVigencia from './AvisosVigencia'
import styles from './Normativa.module.css'

export default function DisposicionesTable({ normaId, ramaId }) {
  const [filas, setFilas] = useState([])
  const [pagina, setPagina] = useState(1)
  const [siguiente, setSiguiente] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { setPagina(1) }, [normaId, ramaId])
  useEffect(() => {
    let activo = true
    api.get('/api/catalogo/disposiciones/', { params: { norma_id: normaId || undefined, rama_id: ramaId || undefined, page: pagina } })
      .then(({ data }) => { if (activo) { setFilas(data.results || data); setSiguiente(Boolean(data.next)); setError('') } })
      .catch(() => { if (activo) { setFilas([]); setError('No se pudieron consultar las disposiciones.') } })
    return () => { activo = false }
  }, [normaId, ramaId, pagina])
  return <section className={styles.panel} aria-label="Disposiciones del catálogo">
    <h2>Disposiciones finales, derogatorias y abrogatorias</h2>
    {error && <p role="alert">{error}</p>}
    <div className={styles.tablaContenedor}><table className={styles.tabla}><thead><tr><th>Norma</th><th>Tipo</th><th>Disposición</th><th>Texto y avisos</th></tr></thead>
      <tbody>{filas.map((d) => <tr key={d.id}><td>{d.norma_nombre}</td><td>{d.tipo}</td><td>{d.numero}</td>
        <td><AvisosVigencia avisos={d.avisos} /><details><summary>Ver disposición</summary>
          <p style={{ whiteSpace: 'pre-wrap' }}>{d.contenido}</p></details></td></tr>)}</tbody>
    </table></div>
    {!filas.length && !error && <p>No hay disposiciones cargadas para estos filtros.</p>}
    <button type="button" disabled={pagina <= 1} onClick={() => setPagina((p) => p - 1)}>Anterior</button>
    <span> Página {pagina} </span>
    <button type="button" disabled={!siguiente} onClick={() => setPagina((p) => p + 1)}>Siguiente</button>
  </section>
}
