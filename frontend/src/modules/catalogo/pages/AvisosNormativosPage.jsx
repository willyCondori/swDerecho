import Modal from '../../../components/ui/Modal'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import normativaApi from '../../../api/normativaApi'
import catalogoApi from '../../../api/catalogoApi'
import useAuthStore from '../../auth/store/authStore'
import RevisionCambioForm from '../components/articulos/RevisionCambioForm'
import styles from '../components/articulos/Normativa.module.css'

const TIPOS = { deroga: 'Derogaciones', abroga: 'Abrogaciones', historico: 'Históricos', modifica: 'Modificaciones', incorpora: 'Incorporaciones', judicial: 'Referencias judiciales', temporal: 'Vigencia y plazos', general: 'Otros avisos' }
const ESTADOS = { pendiente: 'Pendiente', confirmado: 'Confirmado', descartado: 'Descartado', revertido: 'Restaurado' }

function Destino({ cambio, admin, normas, actualizar }) {
  const [abierto, setAbierto] = useState(false)
  const [ocupado, setOcupado] = useState(false)
  const historico = cambio.aviso?.nota_historica
  const informativo = historico || ['general', 'temporal'].includes(cambio.operacion)
  return <li>
    <p><strong>{cambio.referencia.norma || 'Norma del documento'} {cambio.referencia.unidad && `· Artículo ${cambio.referencia.unidad}`}</strong></p>
    {cambio.fecha_efecto && <p>Fecha de efecto: {cambio.fecha_efecto}</p>}
    <p>{TIPOS[cambio.aviso?.categoria_aviso] || TIPOS[cambio.operacion] || 'Aviso'} · {informativo ? 'Informativo' : ESTADOS[cambio.estado_revision]} · Alcance: {cambio.referencia.alcance || 'Por verificar'}</p>
    {!informativo && cambio.destino_catalogo?.encontrado === false && <p>Solo aviso: el destino exacto no está cargado.</p>}
    {cambio.referencia.parte_afectada?.tipo === 'parcial' && <p>Parte afectada: {cambio.referencia.parte_afectada.descripcion}</p>}
    {admin && cambio.estado_revision === 'pendiente' && !informativo && <>
      <button type="button" aria-expanded={abierto} onClick={() => setAbierto((v) => !v)}>{abierto ? 'Cerrar revisión' : 'Revisar este destino'}</button>
      {abierto && <Modal open busy={ocupado} onClose={() => setAbierto(false)}
        title={cambio.operacion === 'abroga' ? 'Revisar abrogación' : 'Revisar derogación'}
        description="Comprueba la fuente y el antes y después previsto antes de confirmar.">
        <details><summary>Fuente del cambio</summary><blockquote>{cambio.cita}</blockquote>
          {cambio.url_fuente && <a href={cambio.url_fuente} target="_blank" rel="noopener noreferrer">Ver publicación oficial</a>}
        </details>
        <RevisionCambioForm cambio={cambio} normas={normas} onBusy={setOcupado}
          onPendiente={() => setAbierto(false)} onActualizado={actualizar} />
      </Modal>}
    </>}
  </li>
}

export default function AvisosNormativosPage() {
  const admin = useAuthStore((s) => s.isAdmin())
  const [params, setParams] = useSearchParams()
  const [buscar, setBuscar] = useState(params.get('buscar') || '')
  const [grupos, setGrupos] = useState([])
  const [normas, setNormas] = useState([])
  const [count, setCount] = useState(0)
  const [siguiente, setSiguiente] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  const pagina = Number(params.get('page')) || 1
  const query = params.toString()
  const cambiar = (campo, valor) => {
    const siguientes = new URLSearchParams(params)
    if (valor) siguientes.set(campo, valor); else siguientes.delete(campo)
    if (campo !== 'page') siguientes.delete('page')
    setParams(siguientes, { replace: true })
  }
  useEffect(() => { setBuscar(params.get('buscar') || '') }, [query])
  useEffect(() => {
    const timer = setTimeout(() => {
      if (buscar !== (params.get('buscar') || '')) cambiar('buscar', buscar.trim())
    }, 350)
    return () => clearTimeout(timer)
  }, [buscar, query])
  useEffect(() => {
    catalogoApi.normas().then(({ data }) => setNormas(data.results || data)).catch(() => {})
  }, [])
  useEffect(() => {
    let activo = true
    setLoading(true); setError('')
    normativaApi.gruposAvisos(Object.fromEntries(new URLSearchParams(query)))
      .then(({ data }) => { if (activo) { setGrupos(data.results || data); setCount(data.count ?? data.length); setSiguiente(Boolean(data.next)) } })
      .catch(() => { if (activo) { setGrupos([]); setError('No se pudieron consultar los avisos normativos.') } })
      .finally(() => { if (activo) setLoading(false) })
    return () => { activo = false }
  }, [query, revision])
  const descargar = async (id) => {
    try {
      const { data } = await catalogoApi.descargarDocumentoNorma(id)
      const url = URL.createObjectURL(data)
      const enlace = document.createElement('a')
      enlace.href = url; enlace.download = `fuente-normativa-${id}.pdf`; enlace.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch { setError('No se pudo descargar el PDF de respaldo.') }
  }
  return <section className={styles.panel} aria-label="Avisos normativos del catálogo">
    <h1>Avisos normativos</h1>
    <p>Consulta las disposiciones y notas que afectan al catálogo. El fundamento se muestra una sola vez; cada destino mantiene su alcance y estado de revisión.</p>
    <div className={styles.controles}>
      <label>Buscar aviso <input type="search" value={buscar} onChange={(e) => setBuscar(e.target.value)} placeholder="Ley, artículo, disposición o texto…" /></label>
      <label>Tipo de aviso <select value={params.get('tipo') || ''} onChange={(e) => cambiar('tipo', e.target.value)}>
        <option value="">Todos los tipos</option>{Object.entries(TIPOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select></label>
      <label>Estado de revisión <select value={params.get('estado_revision') || ''} onChange={(e) => cambiar('estado_revision', e.target.value)}>
        <option value="">Todos los estados</option>{Object.entries(ESTADOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select></label>
      <label>Norma <select value={params.get('norma') || ''} onChange={(e) => cambiar('norma', e.target.value)}>
        <option value="">Todas las normas</option>{normas.map((n) => <option key={n.id} value={n.id}>{n.nombre}</option>)}
      </select></label>
      <button type="button" onClick={() => { setBuscar(''); setParams({}) }}>Limpiar filtros</button>
      <button type="button" disabled={loading} onClick={() => setRevision((v) => v + 1)}>Actualizar</button>
    </div>
    {params.get('articulo') && <p>Mostrando los avisos vinculados al artículo seleccionado. Usa «Limpiar filtros» para consultar todos.</p>}
    {params.get('fuente_norma') && <p>Mostrando los avisos originados en la norma seleccionada.</p>}
    {error && <p role="alert">{error}</p>}
    {loading ? <p role="status">Consultando avisos…</p> : <>
      <p role="status">{count} fundamentos encontrados · Página {pagina}.</p>
      {!grupos.length && !error && <p>No hay avisos que coincidan con los filtros.</p>}
      {grupos.map((g) => <section className={styles.aviso} key={g.id}>
        <h2>{g.norma_causante} · {g.disposicion_fuente}</h2>
        <p>Fecha de la norma causante: {g.fecha || 'Por verificar'} · {g.afectaciones.length} destinos en este filtro.</p>
        <details><summary>Ver fundamento y fuente</summary><blockquote>{g.cita}</blockquote>
          {g.documento_id && <button type="button" onClick={() => descargar(g.documento_id)}>Descargar PDF de respaldo</button>}
          {g.url_fuente && <a href={g.url_fuente} target="_blank" rel="noopener noreferrer">Publicación oficial</a>}
        </details>
        <details><summary>Ver artículos y normas afectados ({g.afectaciones.length})</summary>
          <ul className={styles.lista}>{g.afectaciones.map((c) => <Destino key={c.id} cambio={c} admin={admin} normas={normas} actualizar={() => setRevision((v) => v + 1)} />)}</ul>
        </details>
      </section>)}
      <button type="button" disabled={pagina <= 1} onClick={() => cambiar('page', String(pagina - 1))}>Anterior</button>
      <span>Página {pagina}</span>
      <button type="button" disabled={!siguiente} onClick={() => cambiar('page', String(pagina + 1))}>Siguiente</button>
    </>}
  </section>
}
