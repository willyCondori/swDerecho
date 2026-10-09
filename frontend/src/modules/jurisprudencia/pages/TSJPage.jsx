import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PageHeader from '../../../components/ui/PageHeader'
import DataTable from '../../../components/ui/DataTable'
import Pagination from '../../../components/ui/Pagination'
import useAuthStore from '../../auth/store/authStore'
import jurisprudenciaApi from '../../../api/jurisprudenciaApi'
import useListadoJurisprudencia from '../hooks/useListadoJurisprudencia'
import shared from '../../../styles/shared.module.css'
import styles from './Jurisprudencia.module.css'

export default function TSJPage() {
  const listado = useListadoJurisprudencia(true)
  const puedeEscribir = useAuthStore((s) => s.puedeEscribir())
  const [palabras, setPalabras] = useState('penal')
  const [tarea, setTarea] = useState(() => sessionStorage.getItem('tsj-incorporacion'))
  const [iniciando, setIniciando] = useState(false)
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')
  useEffect(() => {
    if (tarea) sessionStorage.setItem('tsj-incorporacion', tarea)
    else sessionStorage.removeItem('tsj-incorporacion')
  }, [tarea])
  useEffect(() => {
    if (!tarea) return
    const controller = new AbortController()
    let timer
    const consultar = async () => {
      try {
        const { data } = await jurisprudenciaApi.estado(tarea, { signal: controller.signal })
        if (controller.signal.aborted) return
        if (data.estado === 'SUCCESS') {
          setMensaje('Resolución guardada y disponible para el análisis IA.'); setTarea(null); listado.recargar(); return
        }
        if (data.estado === 'FAILURE') { setError(data.error || 'No se pudo incorporar la resolución.'); setMensaje(''); setTarea(null); return }
        setMensaje(data.resumen?.paso || 'Incorporando resolución...')
        timer = setTimeout(consultar, 2000)
      } catch {
        if (!controller.signal.aborted) { setError('No se pudo consultar el progreso. La incorporación puede continuar; recarga la página para volver a consultar.'); setMensaje('') }
      }
    }
    consultar()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [tarea, listado.recargar])
  const incorporar = async (id) => {
    setIniciando(true); setError(''); setMensaje('Iniciando incorporación...')
    try { const { data } = await jurisprudenciaApi.incorporar(id); setTarea(data.task_id) }
    catch (e) { setError(e.response?.data?.detail || 'No se pudo iniciar la incorporación.'); setMensaje('') }
    finally { setIniciando(false) }
  }
  const columnas = [
    { key: 'numero', header: 'Resolución', render: (r) => <><strong>{r.numero || `TSJ ${r.fuente_id}`}</strong><p className={styles.extracto}>{r.extracto}</p></> },
    { key: 'fecha', header: 'Fecha' },
    { key: 'sala', header: 'Sala' },
    { key: 'acciones', header: 'Consulta e incorporación', actions: true, render: (r) => <>
      <a href={r.url_fuente} target="_blank" rel="noopener noreferrer">Fuente oficial</a>
      {r.registro_id ? <Link className={shared.btnSecondary} to={`/jurisprudencia?resolucion=${r.registro_id}`}>Leer guardada</Link>
        : puedeEscribir && <button className={shared.btnSecondary} disabled={Boolean(tarea) || iniciando} onClick={() => incorporar(r.fuente_id)}>Incorporar jurisprudencia</button>}
    </> },
  ]
  return <div className={shared.root}>
    <PageHeader title="Tribunal Supremo de Justicia" subtitle="Consulta resoluciones penales en Genesis e incorpóralas para utilizarlas en el análisis de casos.">
      <a href="https://genesis.tsj.bo" target="_blank" rel="noopener noreferrer" className={shared.btnSecondary}>Abrir Genesis</a>
      <Link className={shared.btnSecondary} to="/jurisprudencia">Ver jurisprudencia guardada</Link>
    </PageHeader>
    <form className={`${styles.filters} ${styles.panel}`} onSubmit={(e) => { e.preventDefault(); listado.buscar({ palabras }) }}>
      <label className={`${shared.field} ${styles.busqueda}`}>Palabras de búsqueda en el TSJ<input className={shared.input} value={palabras} maxLength={150} required onChange={(e) => setPalabras(e.target.value)} placeholder="Por ejemplo: robo agravado" /></label>
      <button className={shared.btnPrimary} disabled={listado.loading || !palabras.trim()}>Buscar en el TSJ</button>
    </form>
    <p className={styles.estado}>La búsqueda consulta el servicio oficial. Las resoluciones incorporadas también se pueden consultar cuando el TSJ no esté disponible.</p>
    {mensaje && <p role="status" className={styles.panel}>{mensaje}</p>}
    {error && <p role="alert" className={shared.errorBanner}>{error}</p>}
    <DataTable columns={columnas} rows={listado.results} loading={listado.loading} error={listado.error} onRetry={listado.recargar} empty={{ text: 'No se encontraron resoluciones para esta búsqueda.' }} ariaLabel="Resultados del TSJ" />
    <Pagination page={listado.page} count={listado.count} pageSize={50} totalPages={listado.totalPages} onPageChange={listado.setPage} itemLabel="resoluciones del TSJ" />
  </div>
}
