"""WebSocket personal sobre ASGI y eventos PostgreSQL entre procesos."""
import asyncio
import json
import logging
import select
import time
from contextlib import asynccontextmanager, suppress
from urllib.parse import urlparse
import psycopg2
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import connection, close_old_connections
from rest_framework_simplejwt.authentication import JWTAuthentication
from modulo_notificaciones.models import Notificacion

logger = logging.getLogger(__name__)


class EventosNotificaciones:
    def __init__(self):
        self.suscriptores = {}
        self.tarea = None

    @asynccontextmanager
    async def suscribir(self, usuario_id):
        cola = asyncio.Queue(maxsize=1)
        self.suscriptores.setdefault(usuario_id, set()).add(cola)
        if self.tarea is None or self.tarea.done():
            self.tarea = asyncio.create_task(self.escuchar())
        try:
            yield cola
        finally:
            self.suscriptores[usuario_id].discard(cola)
            if not self.suscriptores[usuario_id]:
                del self.suscriptores[usuario_id]

    async def escuchar(self):
        while self.suscriptores:
            db = None
            try:
                db = await asyncio.to_thread(psycopg2.connect, **connection.get_connection_params())
                db.autocommit = True
                with db.cursor() as cursor:
                    cursor.execute('LISTEN sw_derecho_notificaciones')
                # Reconciliar al conectar/reconectar: no perder eventos durante el alta.
                for colas in self.suscriptores.values():
                    for cola in colas:
                        if cola.empty(): cola.put_nowait(True)
                while self.suscriptores:
                    listo, _, _ = await asyncio.to_thread(select.select, [db], [], [], 1)
                    if not listo:
                        continue
                    db.poll()
                    while db.notifies:
                        aviso = db.notifies.pop(0)
                        for cola in self.suscriptores.get(int(aviso.payload), ()):
                            if cola.empty(): cola.put_nowait(True)
            except Exception:
                logger.exception('Se perdió el canal de eventos de notificaciones; reconectando')
                await asyncio.sleep(2)
            finally:
                if db is not None:
                    db.close()


eventos = EventosNotificaciones()


def origen_permitido(scope):
    headers = dict(scope.get('headers', []))
    origen = headers.get(b'origin', b'').decode()
    url = urlparse(origen)
    host = headers.get(b'host', b'').decode()
    return url.scheme in ('http', 'https') and (
        origen in settings.CORS_ALLOWED_ORIGINS or
        (url.netloc == host and url.hostname in settings.ALLOWED_HOSTS)
    )


@sync_to_async
def autenticar(token):
    close_old_connections()
    try:
        auth = JWTAuthentication()
        validado = auth.get_validated_token(token)
        usuario = auth.get_user(validado)
        if not usuario.estado:
            raise ValueError('Usuario inactivo')
        return usuario.pk, int(validado['exp'])
    finally:
        close_old_connections()


@sync_to_async
def contador(usuario_id):
    close_old_connections()
    try:
        return Notificacion.objects.filter(usuario_id=usuario_id, leida=False).count()
    finally:
        close_old_connections()


async def notificaciones_websocket(scope, receive, send):
    if scope['path'] != '/ws/notificaciones/' or not origen_permitido(scope):
        await send({'type': 'websocket.close', 'code': 4403})
        return
    if (await receive())['type'] != 'websocket.connect':
        return
    await send({'type': 'websocket.accept'})
    try:
        mensaje = await asyncio.wait_for(receive(), timeout=5)
        texto = mensaje.get('text', '')
        if len(texto) > 8192 or mensaje['type'] != 'websocket.receive':
            raise ValueError('Autenticación requerida')
        usuario_id, expira = await autenticar(json.loads(texto)['access_token'])
    except Exception:
        await send({'type': 'websocket.close', 'code': 4401})
        return
    async with eventos.suscribir(usuario_id) as cola:
        entrada = asyncio.create_task(receive())
        cambio = asyncio.create_task(cola.get())
        try:
            await send({'type': 'websocket.send', 'text': json.dumps({'type': 'contador', 'no_leidas': await contador(usuario_id)})})
            while True:
                pendientes, _ = await asyncio.wait([entrada, cambio], timeout=max(0, expira-time.time()), return_when=asyncio.FIRST_COMPLETED)
                if not pendientes:
                    await send({'type': 'websocket.close', 'code': 4401})
                    break
                if entrada in pendientes:
                    if entrada.result()['type'] == 'websocket.disconnect': break
                    entrada = asyncio.create_task(receive())
                if cambio in pendientes:
                    await send({'type': 'websocket.send', 'text': json.dumps({'type': 'actualizadas', 'no_leidas': await contador(usuario_id)})})
                    cambio = asyncio.create_task(cola.get())
        except OSError:
            pass
        except RuntimeError as error:
            # Uvicorn puede detectar el cierre durante una consulta en curso.
            if 'Unexpected ASGI message' not in str(error):
                raise
        finally:
            for tarea in (entrada, cambio): tarea.cancel()
            for tarea in (entrada, cambio):
                with suppress(asyncio.CancelledError): await tarea
