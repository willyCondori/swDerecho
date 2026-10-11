import asyncio
import json
import time
import select
import psycopg2
from contextlib import asynccontextmanager
from unittest.mock import patch, AsyncMock
from asgiref.testing import ApplicationCommunicator
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.db import connection, transaction
from modulo_notificaciones.realtime import notificaciones_websocket, EventosNotificaciones
from modulo_notificaciones.models import Notificacion
from modulo_usuarios.tests.factories import crear_usuario, crear_rol


@override_settings(ALLOWED_HOSTS=['localhost'], CORS_ALLOWED_ORIGINS=[])
class WebSocketTests(SimpleTestCase):
    def scope(self, origin='http://localhost:8080'):
        return {'type': 'websocket', 'path': '/ws/notificaciones/',
                'headers': [(b'host', b'localhost:8080'), (b'origin', origin.encode())]}

    async def test_rechaza_origen_externo(self):
        app = ApplicationCommunicator(notificaciones_websocket, self.scope('https://intruso.example'))
        self.assertEqual((await app.receive_output())['code'], 4403)
        await app.wait()

    async def test_rechaza_token_invalido(self):
        app = ApplicationCommunicator(notificaciones_websocket, self.scope())
        await app.send_input({'type': 'websocket.connect'})
        self.assertEqual((await app.receive_output())['type'], 'websocket.accept')
        with patch('modulo_notificaciones.realtime.autenticar', new=AsyncMock(side_effect=ValueError())):
            await app.send_input({'type': 'websocket.receive', 'text': '{"access_token":"invalido"}'})
            self.assertEqual((await app.receive_output())['code'], 4401)
        await app.wait()

    async def test_envia_contador_y_actualizacion_y_limpia_al_desconectar(self):
        cola = asyncio.Queue()
        @asynccontextmanager
        async def suscribir(uid):
            self.assertEqual(uid, 7)
            yield cola
        app = ApplicationCommunicator(notificaciones_websocket, self.scope())
        with patch('modulo_notificaciones.realtime.autenticar', new=AsyncMock(return_value=(7, int(time.time())+60))), \
             patch('modulo_notificaciones.realtime.contador', new=AsyncMock(side_effect=[2, 3])), \
             patch('modulo_notificaciones.realtime.eventos.suscribir', side_effect=suscribir):
            await app.send_input({'type': 'websocket.connect'})
            await app.receive_output()
            await app.send_input({'type': 'websocket.receive', 'text': '{"access_token":"prueba"}'})
            self.assertEqual(json.loads((await app.receive_output())['text'])['no_leidas'], 2)
            cola.put_nowait(True)
            self.assertEqual(json.loads((await app.receive_output())['text'])['no_leidas'], 3)
            await app.send_input({'type': 'websocket.disconnect'})
            await app.wait()

    async def test_suscripciones_por_usuario_no_se_mezclan(self):
        bus = EventosNotificaciones()
        with patch.object(bus, 'escuchar', new=AsyncMock()):
            async with bus.suscribir(7) as primera, bus.suscribir(8) as segunda:
                for cola in bus.suscriptores[7]: cola.put_nowait(True)
                self.assertFalse(primera.empty())
                self.assertTrue(segunda.empty())
            self.assertEqual(bus.suscriptores, {})
            await bus.tarea


class EventosPostgresTests(TransactionTestCase):
    def setUp(self):
        self.usuario = crear_usuario('ws.prueba', rol=crear_rol('Abogado'))
        self.db = psycopg2.connect(**connection.get_connection_params())
        self.db.autocommit = True
        with self.db.cursor() as cursor:
            cursor.execute('LISTEN sw_derecho_notificaciones')

    def tearDown(self):
        self.db.close()

    def crear(self):
        return Notificacion.objects.create(usuario=self.usuario, tipo='analisis_completado', titulo='Prueba', mensaje='Texto')

    def recibir(self):
        select.select([self.db], [], [], .3)
        self.db.poll()
        datos = [n.payload for n in self.db.notifies]
        self.db.notifies.clear()
        return datos

    def test_evento_solo_despues_de_commit_y_para_destinatario(self):
        with transaction.atomic():
            self.crear()
            self.assertEqual(self.recibir(), [])
        self.assertEqual(self.recibir(), [str(self.usuario.pk)])
        Notificacion.objects.filter(usuario=self.usuario).update(leida=True)
        self.assertEqual(self.recibir(), [str(self.usuario.pk)])

    def test_rollback_no_envia_notificacion(self):
        try:
            with transaction.atomic():
                self.crear()
                raise ValueError('revertir')
        except ValueError:
            pass
        self.assertEqual(self.recibir(), [])
