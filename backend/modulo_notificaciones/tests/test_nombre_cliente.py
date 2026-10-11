from core.encryption.aes_encryption import encrypt
from modulo_casos.models.caso import Caso
from modulo_clientes.models.cliente import Cliente
from modulo_notificaciones.models import Notificacion, TipoNotificacion
from modulo_usuarios.tests.factories import crear_rol, crear_usuario
from rest_framework.test import APITestCase


class NombreClienteNotificacionTests(APITestCase):
    def setUp(self):
        self.usuario = crear_usuario('avisos.cliente', rol=crear_rol('Abogado'))
        self.cliente = Cliente.objects.create(nombres=encrypt('María'), apellidos=encrypt('Pérez'))
        self.caso = Caso.objects.create(codigo='CASO-AVISO', titulo='Robo',
                                       cliente=self.cliente, usuario=self.usuario)
        self.client.force_authenticate(self.usuario)

    def test_avisos_existentes_muestran_cliente_sin_consultas_por_fila(self):
        for tipo in [TipoNotificacion.CASO_NUEVO, TipoNotificacion.ANALISIS_COMPLETADO,
                     TipoNotificacion.ANALISIS_ERROR, TipoNotificacion.DOCUMENTO_NUEVO]:
            Notificacion.objects.create(usuario=self.usuario, caso=self.caso, tipo=tipo,
                                        titulo='Aviso', mensaje='Caso "Robo" (CASO-AVISO).')
        with self.assertNumQueries(2):  # Paginación y listado con cliente unido.
            respuesta = self.client.get('/api/notificaciones/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data['results']), 4)
        for aviso in respuesta.data['results']:
            self.assertEqual(aviso['mensaje'], 'Caso "Robo" del cliente María Pérez.')
            self.assertEqual(aviso['caso'], str(self.caso.public_id))
        self.assertEqual(Notificacion.objects.first().mensaje, 'Caso "Robo" (CASO-AVISO).')

    def test_aviso_sin_caso_conserva_su_mensaje(self):
        Notificacion.objects.create(usuario=self.usuario, tipo=TipoNotificacion.ANALISIS_ERROR,
                                    titulo='Aviso', mensaje='Mensaje sin caso.')
        respuesta = self.client.get('/api/notificaciones/')
        self.assertEqual(respuesta.data['results'][0]['mensaje'], 'Mensaje sin caso.')

    def test_nombre_ilegible_no_expone_cifrado_ni_identificador(self):
        self.cliente.nombres = self.cliente.apellidos = 'dato ilegible'
        self.cliente.save()
        Notificacion.objects.create(usuario=self.usuario, caso=self.caso,
                                    tipo=TipoNotificacion.CASO_NUEVO,
                                    titulo='Aviso', mensaje='Caso "Robo" (CASO-AVISO).')
        respuesta = self.client.get('/api/notificaciones/')
        self.assertEqual(respuesta.data['results'][0]['mensaje'],
                         'Caso "Robo" del cliente Nombre no disponible.')
