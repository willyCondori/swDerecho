// components/layout/NotificacionesBell.jsx
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useNotificaciones from '../../modules/notificaciones/hooks/useNotificaciones'
import styles from './NotificacionesBell.module.css'

const ICONO_POR_TIPO = {
  caso_nuevo: 'ti-folder-plus',
  analisis_completado: 'ti-circle-check',
  analisis_error: 'ti-alert-triangle',
  documento_nuevo: 'ti-file-text',
  caso_reasignado: 'ti-transfer',
}

function tiempoRelativo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime()
  const min = Math.floor(diffMs / 60000)
  if (min < 1) return 'ahora'
  if (min < 60) return `hace ${min} min`
  const hs = Math.floor(min / 60)
  if (hs < 24) return `hace ${hs} h`
  const dias = Math.floor(hs / 24)
  return `hace ${dias} d`
}

export default function NotificacionesBell() {
  const navigate = useNavigate()
  const { noLeidas, lista, loadingLista, cargarLista, marcarLeida, marcarTodasLeidas } = useNotificaciones()
  const [abierto, setAbierto] = useState(false)
  const contenedorRef = useRef(null)

  useEffect(() => {
    if (abierto) cargarLista()
  }, [abierto, cargarLista])

  // Cerrar al clickear afuera.
  useEffect(() => {
    if (!abierto) return undefined
    const alClickear = (e) => {
      if (contenedorRef.current && !contenedorRef.current.contains(e.target)) {
        setAbierto(false)
      }
    }
    document.addEventListener('mousedown', alClickear)
    return () => document.removeEventListener('mousedown', alClickear)
  }, [abierto])

  const handleClickNotificacion = (n) => {
    if (!n.leida) marcarLeida(n.id)
    setAbierto(false)
    if (n.caso) navigate(`/casos/${n.caso}`)
  }

  return (
    <div className={styles.contenedor} ref={contenedorRef}>
      <button
        type="button"
        className={`${styles.topbarBtn} ${noLeidas > 0 ? styles.conNoLeidas : ''}`}
        aria-label={noLeidas > 0 ? `Notificaciones, ${noLeidas} sin leer` : 'Notificaciones'}
        aria-expanded={abierto}
        onClick={() => setAbierto((v) => !v)}
      >
        <i className="ti ti-bell" aria-hidden="true" />
        {noLeidas > 0 && (
          <span className={styles.badge}>{noLeidas > 9 ? '9+' : noLeidas}</span>
        )}
      </button>

      {abierto && (
        <div className={styles.panel} role="menu">
          <div className={styles.panelHeader}>
            <span>Notificaciones</span>
            {noLeidas > 0 && (
              <button type="button" className={styles.marcarTodasBtn} onClick={marcarTodasLeidas}>
                Marcar todas como leídas
              </button>
            )}
          </div>

          <div className={styles.panelBody}>
            {loadingLista ? (
              <p className={styles.estadoVacio}>Cargando...</p>
            ) : lista.length === 0 ? (
              <p className={styles.estadoVacio}>No tienes notificaciones todavía.</p>
            ) : (
              lista.map((n) => (
                <button
                  key={n.id}
                  type="button"
                  className={`${styles.item} ${!n.leida ? styles.itemNoLeida : ''}`}
                  onClick={() => handleClickNotificacion(n)}
                >
                  <i className={`ti ${ICONO_POR_TIPO[n.tipo] || 'ti-bell'} ${styles.itemIcon}`} aria-hidden="true" />
                  <span className={styles.itemBody}>
                    <span className={styles.itemTitulo}>{n.titulo}</span>
                    <span className={styles.itemMensaje}>{n.mensaje}</span>
                    <span className={styles.itemFecha}>{tiempoRelativo(n.created_at)}</span>
                  </span>
                  {!n.leida && <span className={styles.puntoNoLeida} aria-hidden="true" />}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
