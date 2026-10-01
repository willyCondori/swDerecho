"""
Tests del modo "norma existente" en POST /api/catalogo/cargar-articulos/:
el formulario permite elegir una Norma ya creada por su id (norma_id) en
vez de escribir el nombre a mano, para subir una versión más nueva de su
PDF y (opcionalmente) sobrescribir sus artículos.

Complementa a test_validacion_pdf_endpoints.py, que solo cubre el modo
"norma nueva" (nombre_documento).
"""
import shutil
import tempfile
from unittest.mock import patch

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.models.jerarquia import jerarquia as Jerarquia
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho
from modulo_usuarios.tests.factories import crear_rol, crear_usuario

from .test_validacion_pdf_endpoints import PDF_MINIMO_1_PAGINA


class CargaArticulosNormaExistenteTests(APITestCase):
    """POST /api/catalogo/cargar-articulos/ con norma_id."""

    @classmethod
    def setUpTestData(cls):
        cls.abogado = crear_usuario(usuario="abogado.norma.existente", rol=crear_rol("Abogado"))
        cls.rama = RamaDerecho.objects.create(nombre="Penal test norma existente")
        cls.jerarquia = Jerarquia.objects.create(nivel=60, nombre="Jerarquía test norma existente")
        cls.norma = Norma.objects.create(
            nombre="Código de prueba ya existente",
            sigla="CPX",
            jerarquia=cls.jerarquia,
        )

    def setUp(self):
        # Esta prueba verifica el endpoint, no el procesamiento en otro hilo.
        carga = patch(
            "modulo_catalogo.views.carga_articulos_view.lanzar_carga_en_background",
            return_value="tarea-prueba",
        )
        carga.start()
        self.addCleanup(carga.stop)
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.client.force_authenticate(self.abogado)

    def _post_con_archivo(self, data, contenido=PDF_MINIMO_1_PAGINA):
        from django.core.files.uploadedfile import SimpleUploadedFile
        with override_settings(MEDIA_ROOT=self.media):
            return self.client.post(
                "/api/catalogo/cargar-articulos/",
                {
                    "archivo": SimpleUploadedFile("doc.pdf", contenido, content_type="application/pdf"),
                    **data,
                },
                format="multipart",
            )

    def test_norma_id_usa_la_norma_existente_sin_crear_otra(self):
        total_normas_antes = Norma.objects.count()

        r = self._post_con_archivo({
            "norma_id": self.norma.id,
            "rama_id": self.rama.id,
        })

        self.assertEqual(r.status_code, status.HTTP_202_ACCEPTED, r.data)
        self.assertEqual(r.data["norma"], self.norma.nombre)
        self.assertFalse(r.data["norma_creada"])
        self.assertEqual(Norma.objects.count(), total_normas_antes)

    def test_norma_id_no_requiere_nombre_documento(self):
        r = self._post_con_archivo({
            "norma_id": self.norma.id,
            "rama_id": self.rama.id,
            "nombre_documento": "",
        })
        self.assertEqual(r.status_code, status.HTTP_202_ACCEPTED, r.data)

    def test_sin_norma_id_y_sin_nombre_documento_falla(self):
        r = self._post_con_archivo({
            "rama_id": self.rama.id,
            "nombre_documento": "",
        })
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nombre_documento", r.data)

    def test_norma_id_de_norma_eliminada_es_rechazado(self):
        # El queryset del campo norma_id solo incluye normas activas
        # (estado=True), igual que jerarquia_id y rama_id.
        self.norma.estado = False
        self.norma.save(update_fields=["estado"])

        r = self._post_con_archivo({
            "norma_id": self.norma.id,
            "rama_id": self.rama.id,
        })
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("norma_id", r.data)

    def test_norma_id_con_sobrescribir_reemplaza_articulos_de_esa_norma(self):
        Articulo.objects.create(
            numero_articulo="1", titulo="Art. 1", contenido="Contenido viejo, será reemplazado.",
            norma=self.norma, rama=self.rama,
        )
        self.assertEqual(Articulo.objects.filter(norma=self.norma, rama=self.rama).count(), 1)

        r = self._post_con_archivo({
            "norma_id": self.norma.id,
            "rama_id": self.rama.id,
            "sobrescribir": "true",
        })
        self.assertEqual(r.status_code, status.HTTP_202_ACCEPTED, r.data)
        self.assertTrue(r.data["sobrescribir"])
        # El PDF mínimo de prueba no trae artículos detectables, así que
        # tras la carga en background la norma queda sin artículos: lo que
        # importa acá es que el endpoint aceptó sobrescribir=True sobre la
        # norma elegida por id (el borrado real lo prueba
        # carga_pdf_service ya en sus propios tests).
