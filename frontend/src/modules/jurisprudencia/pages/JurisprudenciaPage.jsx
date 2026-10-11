import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import PageHeader from '../../../components/ui/PageHeader'
import DataTable from '../../../components/ui/DataTable'
import Pagination from '../../../components/ui/Pagination'
import jurisprudenciaApi from '../../../api/jurisprudenciaApi'
import useListadoJurisprudencia from '../hooks/useListadoJurisprudencia'
import LectorResolucion from '../components/LectorResolucion'
import shared from '../../../styles/shared.module.css'
import styles from './Jurisprudencia.module.css'

export default function JurisprudenciaPage() {
  const listado = useListadoJurisprudencia()
  const [filtros, setFiltros] = useState({ search: '', desde: '', hasta: '', sala: '', departamento: '', indexada: '' })
  const [resumen, setResumen] = useState(null)
  const [errorResumen, setErrorResumen] = useState(false)
  const [revisionResumen, setRevisionResumen] = useState(0)
  const [params, setParams] = useSearchParams()
  const seleccion = params.get('resolucion')
  useEffect(() => {
    const controller = new AbortController()
    jurisprudenciaApi.resumen({ signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) { setResumen(data); setErrorResumen(false) } })
      .catch(() => { if (!controller.signal.aborted) setErrorResumen(true) })
    return () => controller.abort()
  }, [revisionResumen])
  const campo = (clave) => ({ value: filtros[clave], onChange: (e) => setFiltros((v) => ({ ...v, [clave]: e.target.value })) })
  const columnas = [
    { key: 'numero', header: 'Resolución', render: (r) => <><strong>{r.numero || `TSJ ${r.fuente_id}`}</strong><p className={styles.extracto}>{r.extracto}…</p></> },
    { key: 'fecha', header: 'Fecha', render: (r) => r.fecha || 'Sin fecha' },
    { key: 'sala', header: 'Sala' },
    { key: 'indexada', header: 'Análisis IA', render: (r) => r.indexada ? 'Disponible' : 'Pendiente de indexar' },
    { key: 'acciones', header: 'Consulta', actions: true, render: (r) => <button className={shared.btnSecondary} onClick={() => setParams({ resolucion: String(r.id) })}>Leer resolución</button> },
  ]
  return <div className={shared.root}>
    <PageHeader title="Jurisprudencia" subtitle="Explora y lee las resoluciones penales guardadas. Las resoluciones listas para IA se utilizan al analizar los hechos de un caso.">
      <button className={shared.btnSecondary} onClick={() => { listado.recargar(); setRevisionResumen(v => v + 1) }}>Actualizar listado</button>
    </PageHeader>
    <section className={styles.panel} aria-label="Estado de la colección">
      {resumen && <div className={styles.stats}>
        <div><strong>{resumen.resoluciones.toLocaleString('es-BO')}</strong><span>Resoluciones guardadas</span></div>
      </div>}
      {errorResumen && <p className={styles.estado} role="alert">No se pudieron cargar las opciones de sala y departamento. Pulsa Actualizar listado para volver a intentar.</p>}
    </section>
    <form className={styles.filters} onSubmit={(e) => { e.preventDefault(); listado.buscar(filtros) }}>
      <label className={`${shared.field} ${styles.busqueda}`}>Buscar por texto, número o expediente<input className={shared.input} {...campo('search')} /></label>
      <label className={shared.field}>Desde<input type="date" className={shared.input} {...campo('desde')} /></label>
      <label className={shared.field}>Hasta<input type="date" className={shared.input} {...campo('hasta')} /></label>
      <label className={shared.field}>Sala<select className={shared.input} {...campo('sala')}><option value="">Todas</option>{resumen?.salas?.map((s) => <option key={s}>{s}</option>)}</select></label>
      <label className={shared.field}>Departamento<select className={shared.input} {...campo('departamento')}><option value="">Todos</option>{resumen?.departamentos?.map((d) => <option key={d}>{d}</option>)}</select></label>
      <label className={shared.field}>Disponible para IA<select className={shared.input} {...campo('indexada')}><option value="">Todas</option><option value="true">Sí</option><option value="false">Pendiente</option></select></label>
      <button className={shared.btnPrimary}>Buscar</button>
      <button type="button" className={shared.btnSecondary} onClick={() => { setFiltros({ search: '', desde: '', hasta: '', sala: '', departamento: '', indexada: '' }); listado.buscar({}) }}>Limpiar</button>
    </form>
    <DataTable columns={columnas} rows={listado.results} loading={listado.loading} error={listado.error} onRetry={listado.recargar} empty={{ text: 'No hay resoluciones que coincidan con los filtros.' }} ariaLabel="Jurisprudencia guardada" />
    <Pagination page={listado.page} count={listado.count} pageSize={25} totalPages={listado.totalPages} onPageChange={listado.setPage} itemLabel="resoluciones" />
    <LectorResolucion id={seleccion} onClose={() => setParams({})} />
  </div>
}
