from django.test import TestCase

from modulo_casos.models.caso import Caso
from modulo_clientes.models.cliente import Cliente
from modulo_notificaciones.models import Notificacion, TipoNotificacion
from modulo_notificaciones.services.notificacion_service import (
    notificar_analisis_completado, notificar_analisis_error,
)
from modulo_usuarios.tests.factories import crear_rol, crear_usuario


class NotificarAnalisisTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.abogado = crear_usuario(usuario="abogado.analisis.notif", rol=crear_rol("Abogado"))
        cls.cliente = Cliente.objects.create(nombres="Cliente", apellidos="Análisis")
        cls.caso = Caso.objects.create(
            codigo="AN-1", titulo="Caso análisis", usuario=cls.abogado, cliente=cls.cliente,
        )

    def test_notificar_analisis_completado_crea_notificacion_al_dueno(self):
        notificar_analisis_completado(self.caso)
        n = Notificacion.objects.get(usuario=self.abogado, tipo=TipoNotificacion.ANALISIS_COMPLETADO)
        self.assertEqual(n.caso_id, self.caso.id)
        self.assertIn(self.caso.codigo, n.mensaje)

    def test_notificar_analisis_error_crea_notificacion_al_dueno(self):
        notificar_analisis_error(self.caso)
        n = Notificacion.objects.get(usuario=self.abogado, tipo=TipoNotificacion.ANALISIS_ERROR)
        self.assertEqual(n.caso_id, self.caso.id)

    def test_crear_notificacion_sin_usuario_no_falla(self):
        from modulo_notificaciones.services.notificacion_service import crear_notificacion
        resultado = crear_notificacion(
            usuario=None, tipo=TipoNotificacion.ANALISIS_COMPLETADO,
            titulo="x", mensaje="y",
        )
        self.assertIsNone(resultado)
