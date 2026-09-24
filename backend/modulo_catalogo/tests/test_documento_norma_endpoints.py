"""
Tests de DocumentoNormaViewSet (/api/catalogo/documentos-norma/) y de que
CargaArticulosView efectivamente deje un registro DocumentoNorma al
guardar el PDF (ver commit "gestión de los PDF subidos para extraer
artículos").

Antes de este modelo, el PDF se guardaba en MEDIA_ROOT pero no quedaba
registrado en ninguna tabla: no había forma de listarlo, descargarlo ni
borrarlo. Estos tests cubren tanto el ViewSet en sí (permisos por rol,
descarga, eliminación física, filtro por norma) como el enganche real con
el endpoint de carga.
"""
import os
import shutil
import tempfile

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from modulo_catalogo.models.documento_norma import DocumentoNorma
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho
from modulo_usuarios.tests.factories import crear_rol, crear_usuario

PDF_MINIMO_1_PAGINA = (
    b"%PDF-1.3\n%\x93\x8c\x8b\x9e ReportLab Generated PDF document (opensource)\n"
    b"1 0 obj\n<<\n/F1 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/BaseFont /Helvetica "
    b"/Encoding /WinAnsiEncoding /Name /F1 /Subtype /Type1 /Type /Font\n>>\nendobj\n"
    b"3 0 obj\n<<\n/Contents 7 0 R /MediaBox [ 0 0 595.2756 841.8898 ] /Parent 6 0 R "
    b"/Resources <<\n/Font 1 0 R /ProcSet [ /PDF /Text /ImageB /ImageC /ImageI ]\n>> "
    b"/Rotate 0 /Trans <<\n\n>> \n  /Type /Page\n>>\nendobj\n4 0 obj\n<<\n/PageMode "
    b"/UseNone /Pages 6 0 R /Type /Catalog\n>>\nendobj\n5 0 obj\n<<\n/Author (anonymous) "
    b"/CreationDate (D:20260922030645+00'00') /Creator (anonymous) /Keywords () "
    b"/ModDate (D:20260922030645+00'00') /Producer (ReportLab PDF Library - "
    b"\\(opensource\\)) \n  /Subject (unspecified) /Title (untitled) /Trapped "
    b"/False\n>>\nendobj\n6 0 obj\n<<\n/Count 1 /Kids [ 3 0 R ] /Type /Pages\n>>\nendobj\n"
    b"7 0 obj\n<<\n/Filter [ /ASCII85Decode /FlateDecode ] /Length 114\n>>\nstream\n"
    b"GapQh0E=F,0U\\H3T\\pNYT^QKk?tc>IP,;W#U1^23ihPEM_?CW4KISi::p;W-:^G0Ccu@*&0$R,8/'1j"
    b"`8Q@/e.SWW0e5Q^q;@(YOku$@?!6%nQ)u~>endstream\nendobj\nxref\n0 8\n0000000000 65535 f \n"
    b"0000000061 00000 n \n0000000092 00000 n \n0000000199 00000 n \n0000000402 00000 n \n"
    b"0000000470 00000 n \n0000000731 00000 n \n0000000790 00000 n \ntrailer\n<<\n/ID \n"
    b"[<e3c564374ff070f36f1213b0fb8d46a5><e3c564374ff070f36f1213b0fb8d46a5>]\n"
    b"% ReportLab generated PDF document -- digest (opensource)\n\n/Info 5 0 R\n"
    b"/Root 4 0 R\n/Size 8\n>>\nstartxref\n994\n%%EOF\n"
)

URL_LISTAR = "/api/catalogo/documentos-norma/"


def _crear_documento_norma(norma, rama=None, ruta_archivo="normas/x.pdf", subido_por=None):
    return DocumentoNorma.objects.create(
        norma=norma,
        rama=rama,
        nombre_original="x.pdf",
        ruta_archivo=ruta_archivo,
        tamano=1234,
        subido_por=subido_por,
    )


class DocumentoNormaPermisosTests(APITestCase):
    """Solo lectura para Asistente; Admin/Abogado con acceso total (salvo destroy, solo Admin)."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario("dn.admin", rol=crear_rol("Administrador"))
        cls.abogado = crear_usuario("dn.abogado", rol=crear_rol("Abogado"))
        cls.asistente = crear_usuario("dn.asistente", rol=crear_rol("Asistente"))
        cls.norma = Norma.objects.create(nombre="Código de prueba", sigla="CPRU")
        cls.documento = _crear_documento_norma(cls.norma)

    def test_anonimo_no_puede_listar(self):
        resp = self.client.get(URL_LISTAR)
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_admin_puede_listar(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(URL_LISTAR)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_abogado_puede_listar(self):
        self.client.force_authenticate(self.abogado)
        resp = self.client.get(URL_LISTAR)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_asistente_puede_listar_solo_lectura(self):
        self.client.force_authenticate(self.asistente)
        resp = self.client.get(URL_LISTAR)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_asistente_no_puede_eliminar(self):
        self.client.force_authenticate(self.asistente)
        resp = self.client.delete(f"{URL_LISTAR}{self.documento.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(DocumentoNorma.objects.filter(pk=self.documento.pk).exists())

    def test_abogado_no_puede_eliminar_solo_admin(self):
        self.client.force_authenticate(self.abogado)
        resp = self.client.delete(f"{URL_LISTAR}{self.documento.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(DocumentoNorma.objects.filter(pk=self.documento.pk).exists())


class DocumentoNormaPorNormaTests(APITestCase):
    """GET /api/catalogo/documentos-norma/por_norma/?norma_id=X"""

    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario("dn.admin2", rol=crear_rol("Administrador"))
        cls.norma_a = Norma.objects.create(nombre="Norma A", sigla="NA")
        cls.norma_b = Norma.objects.create(nombre="Norma B", sigla="NB")
        cls.doc_a1 = _crear_documento_norma(cls.norma_a, ruta_archivo="a/1.pdf")
        cls.doc_a2 = _crear_documento_norma(cls.norma_a, ruta_archivo="a/2.pdf")
        cls.doc_b1 = _crear_documento_norma(cls.norma_b, ruta_archivo="b/1.pdf")

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_devuelve_solo_los_documentos_de_esa_norma(self):
        resp = self.client.get(f"{URL_LISTAR}por_norma/", {"norma_id": self.norma_a.pk})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {d["id"] for d in resp.data}
        self.assertEqual(ids, {self.doc_a1.pk, self.doc_a2.pk})

    def test_norma_sin_documentos_devuelve_lista_vacia(self):
        norma_vacia = Norma.objects.create(nombre="Norma vacía")
        resp = self.client.get(f"{URL_LISTAR}por_norma/", {"norma_id": norma_vacia.pk})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])

    def test_sin_norma_id_devuelve_400(self):
        resp = self.client.get(f"{URL_LISTAR}por_norma/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class DocumentoNormaDescargarTests(APITestCase):
    """GET /api/catalogo/documentos-norma/{id}/descargar/"""

    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario("dn.admin3", rol=crear_rol("Administrador"))
        cls.norma = Norma.objects.create(nombre="Norma descarga")

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.client.force_authenticate(self.admin)

    def test_descarga_el_archivo_si_existe_en_disco(self):
        with override_settings(MEDIA_ROOT=self.media):
            os.makedirs(os.path.join(self.media, "normas"), exist_ok=True)
            ruta_absoluta = os.path.join(self.media, "normas", "archivo.pdf")
            with open(ruta_absoluta, "wb") as f:
                f.write(PDF_MINIMO_1_PAGINA)

            documento = _crear_documento_norma(self.norma, ruta_archivo="normas/archivo.pdf")
            resp = self.client.get(f"{URL_LISTAR}{documento.pk}/descargar/")

            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            self.assertEqual(b"".join(resp.streaming_content), PDF_MINIMO_1_PAGINA)

    def test_404_con_detalle_si_el_archivo_no_existe_en_disco(self):
        with override_settings(MEDIA_ROOT=self.media):
            documento = _crear_documento_norma(self.norma, ruta_archivo="normas/no_existe.pdf")
            resp = self.client.get(f"{URL_LISTAR}{documento.pk}/descargar/")

            self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(resp.data["detail"], "Archivo no encontrado en el servidor.")


class DocumentoNormaEliminarTests(APITestCase):
    """DELETE /api/catalogo/documentos-norma/{id}/ — solo admin, borra fila y archivo físico."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario("dn.admin4", rol=crear_rol("Administrador"))
        cls.norma = Norma.objects.create(nombre="Norma eliminar")

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.client.force_authenticate(self.admin)

    def test_admin_elimina_registro_y_archivo_fisico(self):
        with override_settings(MEDIA_ROOT=self.media):
            ruta_absoluta = os.path.join(self.media, "borrar.pdf")
            with open(ruta_absoluta, "wb") as f:
                f.write(b"contenido")

            documento = _crear_documento_norma(self.norma, ruta_archivo="borrar.pdf")
            resp = self.client.delete(f"{URL_LISTAR}{documento.pk}/")

            self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
            self.assertFalse(DocumentoNorma.objects.filter(pk=documento.pk).exists())
            self.assertFalse(os.path.exists(ruta_absoluta))

    def test_eliminar_no_falla_si_el_archivo_ya_no_esta_en_disco(self):
        with override_settings(MEDIA_ROOT=self.media):
            documento = _crear_documento_norma(self.norma, ruta_archivo="nunca_existio.pdf")
            resp = self.client.delete(f"{URL_LISTAR}{documento.pk}/")

            self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
            self.assertFalse(DocumentoNorma.objects.filter(pk=documento.pk).exists())


class CargaArticulosCreaDocumentoNormaTests(APITestCase):
    """
    Integración: POST /api/catalogo/cargar-articulos/ debe dejar un
    DocumentoNorma con los datos correctos, no solo el archivo en disco.
    """

    @classmethod
    def setUpTestData(cls):
        cls.abogado = crear_usuario("dn.carga", rol=crear_rol("Abogado"))
        cls.rama = RamaDerecho.objects.create(nombre="Penal")

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.client.force_authenticate(self.abogado)

    def test_cargar_un_pdf_valido_crea_el_documento_norma(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        with override_settings(MEDIA_ROOT=self.media):
            resp = self.client.post(
                "/api/catalogo/cargar-articulos/",
                {
                    "archivo": SimpleUploadedFile(
                        "codigo.pdf", PDF_MINIMO_1_PAGINA, content_type="application/pdf"
                    ),
                    "nombre_documento": "Código de prueba para carga",
                    "rama_id": self.rama.id,
                },
                format="multipart",
            )

            self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED, resp.data)
            documento_id = resp.data["documento_norma_id"]

            documento = DocumentoNorma.objects.get(pk=documento_id)
            self.assertEqual(documento.norma.nombre, "Código de prueba para carga")
            self.assertEqual(documento.rama_id, self.rama.id)
            self.assertEqual(documento.nombre_original, "codigo.pdf")
            self.assertEqual(documento.tamano, len(PDF_MINIMO_1_PAGINA))
            self.assertEqual(documento.subido_por_id, self.abogado.id)
            self.assertTrue(os.path.exists(os.path.join(self.media, documento.ruta_archivo)))

    def test_documento_norma_es_consultable_por_norma_tras_la_carga(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        with override_settings(MEDIA_ROOT=self.media):
            resp = self.client.post(
                "/api/catalogo/cargar-articulos/",
                {
                    "archivo": SimpleUploadedFile(
                        "codigo2.pdf", PDF_MINIMO_1_PAGINA, content_type="application/pdf"
                    ),
                    "nombre_documento": "Otro código de prueba",
                    "rama_id": self.rama.id,
                },
                format="multipart",
            )
            norma_id = DocumentoNorma.objects.get(pk=resp.data["documento_norma_id"]).norma_id

            listado = self.client.get(f"{URL_LISTAR}por_norma/", {"norma_id": norma_id})
            self.assertEqual(listado.status_code, status.HTTP_200_OK)
            self.assertEqual(len(listado.data), 1)
            self.assertEqual(listado.data[0]["nombre_original"], "codigo2.pdf")
