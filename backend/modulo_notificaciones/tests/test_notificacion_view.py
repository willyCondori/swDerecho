"""
Tests de GET/POST /api/notificaciones/.

Cubren: que la bandeja es estrictamente personal (ni un Administrador ve
las notificaciones de otro usuario), el filtro ?leida=, el contador para
la campanita, y marcar como leída (una y todas).
"""
import shutil
import tempfile

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from modulo_casos.models.caso import Caso
from modulo_clientes.models.cliente import Cliente
from modulo_documentos.models.documento import TipoDoc
from modulo_notificaciones.models import Notificacion, TipoNotificacion
from modulo_notificaciones.services.notificacion_service import crear_notificacion
from modulo_usuarios.tests.factories import crear_rol, crear_usuario


class NotificacionViewSetTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.abogado_a = crear_usuario(usuario="abogado.notif.a", rol=crear_rol("Abogado"))
        cls.abogado_b = crear_usuario(usuario="abogado.notif.b", rol=crear_rol("Abogado"))
        cls.admin = crear_usuario(usuario="admin.notif", rol=crear_rol("Administrador"))

        cls.notif_a1 = crear_notificacion(
            usuario=cls.abogado_a, tipo=TipoNotificacion.ANALISIS_COMPLETADO,
            titulo="Tu análisis terminó", mensaje="mensaje 1",
        )
        cls.notif_a2 = crear_notificacion(
            usuario=cls.abogado_a, tipo=TipoNotificacion.DOCUMENTO_NUEVO,
            titulo="Nuevo documento", mensaje="mensaje 2",
        )
        cls.notif_a2.leida = True
        cls.notif_a2.save(update_fields=["leida"])

        cls.notif_b1 = crear_notificacion(
            usuario=cls.abogado_b, tipo=TipoNotificacion.ANALISIS_ERROR,
            titulo="Tu análisis falló", mensaje="mensaje de B",
        )

    def test_requiere_autenticacion(self):
        r = self.client.get("/api/notificaciones/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cada_usuario_ve_solo_las_suyas(self):
        self.client.force_authenticate(self.abogado_a)
        r = self.client.get("/api/notificaciones/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = {n["id"] for n in r.data["results"]}
        self.assertEqual(ids, {self.notif_a1.id, self.notif_a2.id})

    def test_admin_no_ve_las_de_otro_usuario(self):
        # A propósito: acá NO aplica ve_todo(). La bandeja de un Administrador
        # muestra solo SUS propias notificaciones, nunca las de abogado_b.
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/notificaciones/")
        self.assertEqual(r.data["results"], [])

    def test_filtro_no_leidas(self):
        self.client.force_authenticate(self.abogado_a)
        r = self.client.get("/api/notificaciones/?leida=false")
        ids = {n["id"] for n in r.data["results"]}
        self.assertEqual(ids, {self.notif_a1.id})

    def test_no_leidas_count(self):
        self.client.force_authenticate(self.abogado_a)
        r = self.client.get("/api/notificaciones/no_leidas_count/")
        self.assertEqual(r.data["no_leidas"], 1)

    def test_marcar_leida(self):
        self.client.force_authenticate(self.abogado_a)
        r = self.client.post(f"/api/notificaciones/{self.notif_a1.id}/marcar_leida/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["leida"])
        self.notif_a1.refresh_from_db()
        self.assertTrue(self.notif_a1.leida)

    def test_no_puede_marcar_leida_una_notificacion_ajena(self):
        self.client.force_authenticate(self.abogado_a)
        r = self.client.post(f"/api/notificaciones/{self.notif_b1.id}/marcar_leida/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_marcar_todas_leidas(self):
        self.client.force_authenticate(self.abogado_a)
        r = self.client.post("/api/notificaciones/marcar_todas_leidas/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["actualizadas"], 1)  # solo notif_a1 estaba sin leer
        self.assertEqual(
            Notificacion.objects.filter(usuario=self.abogado_a, leida=False).count(), 0
        )
        # No le tocó nada a abogado_b.
        self.notif_b1.refresh_from_db()
        self.assertFalse(self.notif_b1.leida)


class DocumentoNuevoNotificaTests(APITestCase):
    """El disparador real: subir un documento al caso de OTRO usuario."""

    @classmethod
    def setUpTestData(cls):
        cls.dueno = crear_usuario(usuario="dueno.caso.notif", rol=crear_rol("Abogado"))
        cls.admin = crear_usuario(usuario="admin.sube.doc", rol=crear_rol("Administrador"))
        cls.cliente = Cliente.objects.create(nombres="Cliente", apellidos="Notif")
        cls.tipo_doc = TipoDoc.objects.create(tipo="Prueba")
        cls.caso = Caso.objects.create(
            codigo="NOTIF-1", titulo="Caso notificación", usuario=cls.dueno, cliente=cls.cliente,
        )

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)

    def _subir(self, usuario):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_authenticate(usuario)
        with override_settings(MEDIA_ROOT=self.media):
            return self.client.post(
                "/api/documentos/documentos/",
                {
                    "caso": self.caso.id,
                    "tipo_documento": self.tipo_doc.id,
                    "archivo": SimpleUploadedFile("prueba.txt", b"contenido", content_type="text/plain"),
                },
                format="multipart",
            )

    def test_otro_usuario_sube_documento_notifica_al_dueno(self):
        r = self._subir(self.admin)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

        notifs = Notificacion.objects.filter(usuario=self.dueno, tipo=TipoNotificacion.DOCUMENTO_NUEVO)
        self.assertEqual(notifs.count(), 1)
        self.assertEqual(notifs.first().caso_id, self.caso.id)

    def test_el_dueno_sube_su_propio_documento_no_se_autonotifica(self):
        r = self._subir(self.dueno)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(
            Notificacion.objects.filter(usuario=self.dueno, tipo=TipoNotificacion.DOCUMENTO_NUEVO).count(),
            0,
        )
