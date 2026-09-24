"""
GET /api/documentos/documentos/por_caso/, /api/documentos/tipo-doc/, etc.

modulo_documentos/urls.py registra 4 recursos (tipo-doc, documentos,
plantillas, documentos-generados) bajo el prefijo "api/documentos/" del
proyecto, así que ninguno vive en la raíz de "api/documentos/" ni en la
raíz de la API. Estos tests fijan esas URLs reales: si alguien vuelve a
tocar la estructura del router sin actualizar frontend/src/api/documentosApi.js,
esta suite se cae en vez de que el frontend reciba un 404 en silencio.
"""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from pypdf import PdfWriter
from rest_framework import status
from rest_framework.test import APITestCase

from modulo_casos.models.caso import Caso
from modulo_clientes.models.cliente import Cliente
from modulo_documentos.models.documento import DocumentoCaso, TipoDoc
from modulo_usuarios.tests.factories import crear_rol, crear_usuario


def _pdf_valido_minimo() -> bytes:
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(buffer)
    return buffer.getvalue()

URL_TIPO_DOC   = "/api/documentos/tipo-doc/"
URL_DOCUMENTOS = "/api/documentos/documentos/"


class DocumentosUrlsTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario("doc.usuario", rol=crear_rol("Abogado"))
        cls.cliente = Cliente.objects.create(nombres="Cliente", apellidos="Docs")
        cls.caso = Caso.objects.create(
            codigo="CASO-DOCS-1", titulo="Caso docs", descripcion="",
            usuario=cls.usuario, cliente=cls.cliente,
        )
        cls.tipo = TipoDoc.objects.create(tipo="respaldo")

    def setUp(self):
        self.client.force_authenticate(self.usuario)

    def test_tipo_doc_vive_bajo_api_documentos(self):
        resp = self.client.get(URL_TIPO_DOC)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_tipo_doc_no_esta_en_la_raiz_de_la_api(self):
        # El caso que reportó el usuario: /api/tipo-doc/ (sin "documentos/")
        # no existe — solo /api/documentos/tipo-doc/.
        resp = self.client.get("/api/tipo-doc/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_documentos_no_vive_en_la_raiz_de_api_documentos(self):
        # /api/documentos/ a secas es la raíz del router (lista de
        # endpoints), no el listado de DocumentoCaso.
        resp = self.client.get("/api/documentos/")
        self.assertNotIn("results", resp.data if isinstance(resp.data, dict) else {})

    def test_por_caso_responde_en_la_url_real(self):
        DocumentoCaso.objects.create(
            caso=self.caso, nombre_original="respaldo.pdf", ruta_archivo="x/respaldo.pdf",
            tipo_archivo="pdf", tamano=100, tipo_documento=self.tipo,
        )
        resp = self.client.get(f"{URL_DOCUMENTOS}por_caso/", {"caso_id": self.caso.pk})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_subir_documento_en_la_url_real(self):
        pdf = SimpleUploadedFile("respaldo.pdf", _pdf_valido_minimo(), content_type="application/pdf")
        resp = self.client.post(URL_DOCUMENTOS, {
            "caso": self.caso.pk, "archivo": pdf, "tipo_documento": self.tipo.pk,
        }, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

    def test_descargar_en_la_url_real(self):
        doc = DocumentoCaso.objects.create(
            caso=self.caso, nombre_original="respaldo.pdf", ruta_archivo="no/existe.pdf",
            tipo_archivo="pdf", tamano=100, tipo_documento=self.tipo,
        )
        resp = self.client.get(f"{URL_DOCUMENTOS}{doc.pk}/descargar/")
        # El archivo físico no existe en este test (no se subió al disco),
        # pero la URL en sí debe resolver a la vista, no dar 404 de ruteo.
        self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])
        if resp.status_code == status.HTTP_404_NOT_FOUND:
            self.assertEqual(resp.data.get("detail"), "Archivo no encontrado en el servidor.")
