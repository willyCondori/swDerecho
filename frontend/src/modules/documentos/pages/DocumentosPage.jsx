import { Link } from 'react-router-dom'
import useAuthStore from '../../auth/store/authStore'
import useDocumentosNormativos from '../hooks/useDocumentosNormativos'
import VerPdfButton from '../components/VerPdfButton'
import PageHeader from '../../../components/ui/PageHeader'
import SearchField from '../../../components/ui/SearchField'
import DataTable from '../../../components/ui/DataTable'
import Pagination from '../../../components/ui/Pagination'
import { dialogs } from '../../../components/ui/dialogs'
import { formatTamano } from '../utils/descargas'
import { formatFechaHora } from '../../casos/utils/etapas'
import shared from '../../../styles/shared.module.css'
import styles from './DocumentosPage.module.css'

export default function DocumentosPage() {
  const admin = useAuthStore((s) => s.isAdmin())
  const puedeEscribir = useAuthStore((s) => s.puedeEscribir())
  const datos = useDocumentosNormativos()
  const eliminar = async (documento) => {
    if (await dialogs.confirm(`¿Eliminar el PDF «${documento.nombre_original}» de «${documento.norma_nombre}»? Los artículos se conservan. Los PDF que respaldan avisos o historial no pueden eliminarse.`)) {
      await datos.ejecutar(documento, true)
    }
  }
  const columns = [
    { key: 'nombre_original', header: 'Documento PDF', render: (doc) => <span className={styles.filename}>{doc.nombre_original}</span> },
    { key: 'norma_nombre', header: 'Norma' },
    { key: 'rama_nombre', header: 'Rama', render: (doc) => doc.rama_nombre || 'Sin rama' },
    { key: 'vigente', header: 'Versión del archivo', render: (doc) => doc.vigente ? 'Actual' : 'Reemplazado' },
    { key: 'created_at', header: 'Registro', render: (doc) => formatFechaHora(doc.created_at) },
    { key: 'tamano', header: 'Tamaño', render: (doc) => formatTamano(doc.tamano) },
    { key: 'acciones', header: 'Acciones', actions: true, render: (doc) => <>
      <VerPdfButton documentoId={doc.id} nombre={doc.nombre_original} className={shared.btnSecondary} />
      <button type="button" className={shared.btnSecondary} disabled={datos.ocupado !== null}
        onClick={() => datos.ejecutar(doc)} aria-label={`Descargar ${doc.nombre_original}`}>Descargar</button>
      {admin && <button type="button" className={shared.btnDanger} disabled={datos.ocupado !== null}
        onClick={() => eliminar(doc)} aria-label={`Eliminar ${doc.nombre_original}`}>Eliminar</button>}
    </> },
  ]
  return <div className={shared.root}>
    <PageHeader title="Documentos de normas" subtitle="Consulta los PDF de las normas jurídicas y sus versiones. La versión del archivo no indica la vigencia jurídica de la norma.">
      {puedeEscribir && <Link className={shared.btnPrimary} to="/catalogo/cargar">Cargar PDF de norma</Link>}
    </PageHeader>
    <div className={styles.filters}>
      <SearchField value={datos.filtros.search} onChange={(v) => datos.filtrar('search', v)} label="Buscar documento o norma" placeholder="Buscar documento o norma..." clearable />
      <label className={shared.field}>Norma<select className={shared.input} value={datos.filtros.norma_id} onChange={(e) => datos.filtrar('norma_id', e.target.value)}>
        <option value="">Todas las normas</option>{datos.normas.map((n) => <option key={n.id} value={n.id}>{n.nombre}</option>)}
      </select></label>
      <label className={shared.field}>Rama<select className={shared.input} value={datos.filtros.rama_id} onChange={(e) => datos.filtrar('rama_id', e.target.value)}>
        <option value="">Todas las ramas</option>{datos.ramas.map((r) => <option key={r.id} value={r.id}>{r.nombre}</option>)}
      </select></label>
      <label className={shared.field}>Versión del archivo<select className={shared.input} value={datos.filtros.vigente} onChange={(e) => datos.filtrar('vigente', e.target.value)}>
        <option value="">Todas las versiones</option><option value="true">Actual</option><option value="false">Reemplazado</option>
      </select></label>
      <button type="button" className={shared.btnSecondary} onClick={datos.limpiar}>Limpiar filtros</button>
    </div>
    {datos.catalogoError && <p role="alert" className={shared.errorBanner}>{datos.catalogoError}</p>}
    <DataTable columns={columns} rows={datos.results} loading={datos.loading} error={datos.error} onRetry={datos.recargar}
      empty={{ text: 'No hay documentos que coincidan con los filtros.' }} ariaLabel="Documentos de normas" />
    <Pagination page={datos.page} count={datos.count} pageSize={datos.pageSize} totalPages={Math.ceil(datos.count / datos.pageSize)} onPageChange={datos.setPage} itemLabel="documentos" />
  </div>
}
