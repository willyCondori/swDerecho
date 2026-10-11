from unittest.mock import patch

from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from modulo_catalogo.models.rama import RamaDerecho
from modulo_clientes.models.cliente import Cliente
from modulo_casos.models.caso import Caso
from modulo_notificaciones.models import Notificacion, TipoNotificacion
from modulo_usuarios.models.usuario import Usuario
from modulo_usuarios.tests.factories import crear_perfil, crear_rol, crear_usuario


class CasoNuevoNotificacionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Las migraciones pueden haber creado administradores iniciales.
        # También deben recibir el aviso: no asumir una base vacía.
        administradores_previos = set(Usuario.objects.filter(
            estado=True, rol__nombre__iexact="Administrador",
        ).values_list("pk", flat=True))
        cls.admin = crear_usuario("admin.casos", rol=crear_rol("Administrador"))
        cls.admin2 = crear_usuario("admin2.casos", rol=cls.admin.rol)
        cls.destinatarios = administradores_previos | {cls.admin.pk, cls.admin2.pk}
        cls.inactivo = crear_usuario("admin.inactivo", rol=cls.admin.rol, estado=False)
        cls.abogado = crear_usuario("abogado.creador", rol=crear_rol("Abogado"))
        crear_perfil(cls.abogado, nombres="Ana", apellidos="Quispe")
        cls.asistente = crear_usuario("asistente.casos", rol=crear_rol("Asistente"))
        cls.cliente = Cliente.objects.create(nombres="Cliente", apellidos="Prueba")
        cls.rama = RamaDerecho.objects.create(nombre="Penal notificaciones")

    def setUp(self):
        self.client.force_authenticate(self.abogado)
        self.datos = {
            "titulo": "Nuevo caso de prueba",
            "descripcion": "Descripción del caso para probar las notificaciones.",
            "rama_detectada_id": self.rama.pk,
            "cliente_id": str(self.cliente.public_id),
        }

    def avisos(self):
        return Notificacion.objects.filter(tipo=TipoNotificacion.CASO_NUEVO)

    def test_cliente_existente_avisa_a_todos_los_administradores_activos(self):
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post("/api/casos/", self.datos, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        avisos = self.avisos().filter(caso__public_id=respuesta.data["id"])
        self.assertSetEqual(set(avisos.values_list("usuario_id", flat=True)),
                            self.destinatarios)
        for aviso in avisos:
            self.assertIn("Ana Quispe (abogado.creador)", aviso.mensaje)
            self.assertIn(respuesta.data["codigo"], aviso.mensaje)
            self.assertIn(self.datos["titulo"], aviso.mensaje)
            self.assertFalse(aviso.leida)
        self.client.force_authenticate(self.admin)
        bandeja = self.client.get("/api/notificaciones/")
        self.assertEqual(bandeja.status_code, 200)
        self.assertTrue(any(n["caso"] == respuesta.data["id"]
                            for n in bandeja.data["results"]))

    def test_creacion_con_cliente_tambien_notifica(self):
        datos = {**self.datos, "nombres": "Maria", "apellidos": "Perez"}
        datos.pop("cliente_id")
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post("/api/casos/crear_con_cliente/", datos, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertEqual(self.avisos().filter(caso__public_id=respuesta.data["id"]).count(), len(self.destinatarios))

    def test_creacion_invalida_no_notifica(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            respuesta = self.client.post("/api/casos/", {**self.datos, "titulo": "x"}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(callbacks, [])
        self.assertFalse(self.avisos().exists())

    def test_rollback_no_deja_notificaciones(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with transaction.atomic():
                respuesta = self.client.post("/api/casos/", self.datos, format="json")
                self.assertEqual(respuesta.status_code, 201)
                transaction.set_rollback(True)
        self.assertEqual(callbacks, [])
        self.assertFalse(self.avisos().exists())
        self.assertFalse(Caso.objects.filter(public_id=respuesta.data["id"]).exists())

    def test_fallo_de_notificacion_no_impide_crear_el_caso(self):
        with patch("modulo_notificaciones.services.notificacion_service.Notificacion.objects.create",
                   side_effect=IntegrityError("fallo simulado")), self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post("/api/casos/", self.datos, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertTrue(Caso.objects.filter(public_id=respuesta.data["id"]).exists())

    def test_creador_administrador_sin_perfil_se_identifica_por_usuario(self):
        self.client.force_authenticate(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post("/api/casos/", self.datos, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertEqual(self.avisos().count(), len(self.destinatarios))
        self.assertIn("admin.casos creó", self.avisos().first().mensaje)
