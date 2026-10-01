"""
Tests de integración: los dos endpoints que reciben un archivo .pdf real
(la carga masiva de artículos y el PDF adjunto a un caso) rechazan un
archivo con extensión .pdf pero contenido ajeno o corrupto.

Complementan a core.tests.test_validar_pdf, que prueba el helper aislado.
"""
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from modulo_catalogo.models.rama import RamaDerecho
from modulo_usuarios.tests.factories import crear_rol, crear_usuario

PDF_MINIMO_1_PAGINA = b"%PDF-1.3\n%\x93\x8c\x8b\x9e ReportLab Generated PDF document (opensource)\n1 0 obj\n<<\n/F1 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/BaseFont /Helvetica /Encoding /WinAnsiEncoding /Name /F1 /Subtype /Type1 /Type /Font\n>>\nendobj\n3 0 obj\n<<\n/Contents 7 0 R /MediaBox [ 0 0 595.2756 841.8898 ] /Parent 6 0 R /Resources <<\n/Font 1 0 R /ProcSet [ /PDF /Text /ImageB /ImageC /ImageI ]\n>> /Rotate 0 /Trans <<\n\n>> \n  /Type /Page\n>>\nendobj\n4 0 obj\n<<\n/PageMode /UseNone /Pages 6 0 R /Type /Catalog\n>>\nendobj\n5 0 obj\n<<\n/Author (anonymous) /CreationDate (D:20260922030645+00'00') /Creator (anonymous) /Keywords () /ModDate (D:20260922030645+00'00') /Producer (ReportLab PDF Library - \\(opensource\\)) \n  /Subject (unspecified) /Title (untitled) /Trapped /False\n>>\nendobj\n6 0 obj\n<<\n/Count 1 /Kids [ 3 0 R ] /Type /Pages\n>>\nendobj\n7 0 obj\n<<\n/Filter [ /ASCII85Decode /FlateDecode ] /Length 114\n>>\nstream\nGapQh0E=F,0U\\H3T\\pNYT^QKk?tc>IP,;W#U1^23ihPEM_?CW4KISi::p;W-:^G0Ccu@*&0$R,8/'1j`8Q@/e.SWW0e5Q^q;@(YOku$@?!6%nQ)u~>endstream\nendobj\nxref\n0 8\n0000000000 65535 f \n0000000061 00000 n \n0000000092 00000 n \n0000000199 00000 n \n0000000402 00000 n \n0000000470 00000 n \n0000000731 00000 n \n0000000790 00000 n \ntrailer\n<<\n/ID \n[<e3c564374ff070f36f1213b0fb8d46a5><e3c564374ff070f36f1213b0fb8d46a5>]\n% ReportLab generated PDF document -- digest (opensource)\n\n/Info 5 0 R\n/Root 4 0 R\n/Size 8\n>>\nstartxref\n994\n%%EOF\n"


class CargaArticulosValidacionContenidoTests(APITestCase):
    """POST /api/catalogo/cargar-articulos/"""

    @classmethod
    def setUpTestData(cls):
        cls.abogado = crear_usuario(usuario="abogado1", rol=crear_rol("Abogado"))
        cls.rama = RamaDerecho.objects.create(nombre="Penal")

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.client.force_authenticate(self.abogado)

    def _post(self, contenido, nombre="doc.pdf"):
        with override_settings(MEDIA_ROOT=self.media):
            return self.client.post(
                "/api/catalogo/cargar-articulos/",
                {
                    "archivo": SimpleUploadedFile(nombre, contenido, content_type="application/pdf"),
                    "nombre_documento": "Documento de prueba",
                    "rama_id": self.rama.id,
                },
                format="multipart",
            )

    def test_un_ejecutable_renombrado_a_pdf_se_rechaza(self):
        r = self._post(b"MZ\x90\x00\x03\x00\x00\x00binario que no es un pdf")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("firma", str(r.data["archivo"]))

    def test_un_pdf_corrupto_se_rechaza(self):
        r = self._post(b"%PDF-1.4\nesto no tiene estructura de pdf valida")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("dañado", str(r.data["archivo"]))

    def test_un_pdf_valido_pasa_la_validacion(self):
        r = self._post(PDF_MINIMO_1_PAGINA)
        self.assertEqual(r.status_code, status.HTTP_202_ACCEPTED, r.data)


class SubirPdfCasoValidacionContenidoTests(APITestCase):
    """POST /api/casos/{id}/subir_pdf/"""

    @classmethod
    def setUpTestData(cls):
        from modulo_catalogo.models.rama import RamaDerecho as Rama
        from modulo_clientes.models.cliente import Cliente
        from modulo_casos.models.caso import Caso
        from core.encryption.aes_encryption import encrypt

        cls.abogado = crear_usuario(usuario="abogado2", rol=crear_rol("Abogado"))
        rama = Rama.objects.create(nombre="Civil")
        cliente = Cliente.objects.create(nombres=encrypt("Ana"), apellidos=encrypt("Rojas"))
        cls.caso = Caso.objects.create(
            codigo="CASO-VAL0001", titulo="Caso de prueba", descripcion="x",
            usuario=cls.abogado, cliente=cliente, rama_detectada=rama,
        )

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.client.force_authenticate(self.abogado)

    def _subir(self, contenido, nombre="caso.pdf"):
        with override_settings(MEDIA_ROOT=self.media):
            return self.client.post(
                f"/api/casos/{self.caso.pk}/subir_pdf/",
                {"archivo_pdf": SimpleUploadedFile(nombre, contenido, content_type="application/pdf")},
                format="multipart",
            )

    def test_contenido_ajeno_con_extension_pdf_se_rechaza(self):
        r = self._subir(b"esto es texto comun, no un pdf, aunque el nombre diga .pdf")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_un_pdf_valido_se_adjunta_correctamente(self):
        r = self._subir(PDF_MINIMO_1_PAGINA)
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)

    def test_un_docx_con_extension_pdf_tambien_se_rechaza(self):
        # firma ZIP (PK\x03\x04), típica de .docx — no es %PDF-
        r = self._subir(b"PK\x03\x04contenido de un docx real pero con nombre .pdf")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
