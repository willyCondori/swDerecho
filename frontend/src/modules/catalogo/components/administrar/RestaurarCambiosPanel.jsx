import { useEffect, useState } from 'react'
import normativaApi from '../../../../api/normativaApi'
import catalogoApi from '../../../../api/catalogoApi'
import ComparacionCambioArticulo from '../articulos/ComparacionCambioArticulo'
import styles from '../articulos/Normativa.module.css'

function RestauracionDetalle({ cambio, onActualizado }) {
  const [vista, setVista] = useState(null)
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const abrir = async () => {
    setOcupado(true); setError('')
    try { const { data } = await normativaApi.prepararRestauracion(cambio.id); setVista(data) }
    catch { setError('No se pudo preparar la restauración.') }
    finally { setOcupado(false) }
  }
  const restaurar = async () => {
    setOcupado(true); setError('')
    try {
      await normativaApi.restaurarCambio(cambio.id)
      onActualizado()
    } catch (e) { setError(e.response?.data?.detail || 'No se pudo restaurar el cambio.') }
    finally { setOcupado(false) }
  }
  return <div>
    <p><strong>{cambio.referencia.norma || 'Norma del documento'} {cambio.referencia.unidad}</strong> · {cambio.referencia.alcance}</p>
    <p>Cambio registrado: {cambio.operacion === 'abroga' ? 'abrogación de la norma' : cambio.referencia.parte_afectada?.tipo === 'parcial' ? `retirada parcial del texto (${cambio.referencia.parte_afectada.descripcion})` : 'derogación total; el texto se conserva como respaldo histórico'}.</p>
    {cambio.estado_revision === 'revertido'
      ? <p>Restauración registrada el {new Date(cambio.restaurado_at).toLocaleString('es-BO')}.</p>
      : <>
        {!vista && <button type="button" disabled={ocupado} onClick={abrir}>{ocupado ? 'Preparando…' : 'Revisar restauración'}</button>}
        {vista && <>
          <p>Esta acción revierte la confirmación registrada en el sistema. Se conservarán la fuente y el historial.</p>
          <p>{vista.historial.length} artículos vinculados. Se revierte la confirmación completa, las otras afectaciones del catálogo se mantienen.</p>
          {!vista.restaurable && <p role="alert">{vista.detalle}</p>}
          {vista.historial.map((h) => <details key={h.id}><summary>Artículo {h.numero_articulo} · Ver texto antes de restaurar y texto a recuperar</summary>
            <ComparacionCambioArticulo registro={{ ...h, operacion: h.operacion || cambio.operacion }} restaurar />
          </details>)}
          <button type="button" disabled={ocupado || !vista.restaurable} onClick={restaurar}>{ocupado ? 'Restaurando…' : 'Confirmar restauración'}</button>
          <button type="button" disabled={ocupado} onClick={() => setVista(null)}>Cancelar</button>
        </>}
      </>}
    {error && <p role="alert">{error}</p>}
  </div>
}

export default function RestaurarCambiosPanel() {
  const [grupos, setGrupos] = useState([])
  const [normas, setNormas] = useState([])
  const [norma, setNorma] = useState('')
  const [busqueda, setBusqueda] = useState('')
  const [buscar, setBuscar] = useState('')
  const [estado, setEstado] = useState('confirmado')
  const [pagina, setPagina] = useState(1)
  const [siguiente, setSiguiente] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  const [mensaje, setMensaje] = useState('')
  useEffect(() => { catalogoApi.normas().then(({ data }) => setNormas(data.results || data)).catch(() => {}) }, [])
  useEffect(() => {
    let activo = true
    setLoading(true); setError('')
    normativaApi.gruposAvisos({ estado_revision: estado, operaciones: 'deroga,abroga', page: pagina, ...(norma ? { norma } : {}), ...(buscar ? { buscar } : {}) })
      .then(({ data }) => { if (activo) { setGrupos((data.results || data).map((g) => ({ ...g, afectaciones: g.afectaciones.filter((c) => ['deroga', 'abroga'].includes(c.operacion)) })).filter((g) => g.afectaciones.length)); setSiguiente(Boolean(data.next)) } })
      .catch(() => { if (activo) { setGrupos([]); setError('No se pudieron consultar los cambios para restaurar.') } })
      .finally(() => { if (activo) setLoading(false) })
    return () => { activo = false }
  }, [estado, norma, buscar, pagina, revision])
  return <section className={styles.panel}>
    <h2>Restaurar cambios confirmados</h2>
    <p>Corrige una confirmación hecha por error. Si se retiró una parte del artículo, podrás recuperar su texto anterior cuando no haya cambios posteriores. Revertir la marca registrada no modifica la ley de origen.</p>
    <form className={styles.controles} onSubmit={(e) => { e.preventDefault(); setBuscar(busqueda.trim()); setPagina(1) }}>
      <label>Buscar cambio <input type="search" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} placeholder="Ley, artículo o disposición" /></label>
      <button type="submit">Buscar</button>
      <label>Norma <select value={norma} onChange={(e) => { setNorma(e.target.value); setPagina(1) }}>
        <option value="">Todas las normas</option>{normas.map((n) => <option key={n.id} value={n.id}>{n.nombre}</option>)}
      </select></label>
      <label>Estado <select value={estado} onChange={(e) => { setEstado(e.target.value); setPagina(1) }}>
        <option value="confirmado">Confirmaciones para restaurar</option><option value="revertido">Restauraciones realizadas</option>
      </select></label>
    </form>
    {mensaje && <p role="status">{mensaje}</p>}
    {error && <p role="alert">{error}</p>}
    {loading ? <p role="status">Consultando cambios…</p> : <>
      {!grupos.length && !error && <p>No hay cambios en este filtro.</p>}
      {grupos.map((g) => <section className={styles.aviso} key={g.id}>
        <h3>{g.norma_causante} · {g.disposicion_fuente}</h3>
        <details><summary>Ver fundamento original</summary><blockquote>{g.cita}</blockquote></details>
        <ul className={styles.lista}>{g.afectaciones.map((c) => <li key={c.id}><RestauracionDetalle cambio={c} onActualizado={() => {
          setMensaje('Restauración registrada. Puedes consultarla en Restauraciones realizadas y en Historial de cambios.')
          setRevision((v) => v + 1)
        }} /></li>)}</ul>
      </section>)}
      <button type="button" disabled={pagina <= 1} onClick={() => setPagina((v) => v - 1)}>Anterior</button><span>Página {pagina}</span>
      <button type="button" disabled={!siguiente} onClick={() => setPagina((v) => v + 1)}>Siguiente</button>
    </>}
  </section>
}
