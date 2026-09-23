"""
Tests del borrado lógico y la restauración de normas:

    DELETE /api/catalogo/normas/{id}/          — eliminar (lógico) [admin]
    POST   /api/catalogo/normas/{id}/activar/  — restaurar          [admin]
    GET    /api/catalogo/normas/?estado=false  — normas eliminadas  [admin]

Además verifica que los artículos de una norma eliminada dejan de verse
en el catálogo, no entran al ranking del análisis, y que la carga de PDF
no crea una norma duplicada cuando la que existe está eliminada.
"""

# PDF mínimo (una página en blanco) para pasar la validación real del
# contenido, que ahora abre el archivo con pypdf.
PDF_MINIMO_1_PAGINA = b"%PDF-1.3\n%\x93\x8c\x8b\x9e ReportLab Generated PDF document (opensource)\n1 0 obj\n<<\n/F1 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/BaseFont /Helvetica /Encoding /WinAnsiEncoding /Name /F1 /Subtype /Type1 /Type /Font\n>>\nendobj\n3 0 obj\n<<\n/Contents 7 0 R /MediaBox [ 0 0 595.2756 841.8898 ] /Parent 6 0 R /Resources <<\n/Font 1 0 R /ProcSet [ /PDF /Text /ImageB /ImageC /ImageI ]\n>> /Rotate 0 /Trans <<\n\n>> \n  /Type /Page\n>>\nendobj\n4 0 obj\n<<\n/PageMode /UseNone /Pages 6 0 R /Type /Catalog\n>>\nendobj\n5 0 obj\n<<\n/Author (anonymous) /CreationDate (D:20260922030645+00'00') /Creator (anonymous) /Keywords () /ModDate (D:20260922030645+00'00') /Producer (ReportLab PDF Library - \\(opensource\\)) \n  /Subject (unspecified) /Title (untitled) /Trapped /False\n>>\nendobj\n6 0 obj\n<<\n/Count 1 /Kids [ 3 0 R ] /Type /Pages\n>>\nendobj\n7 0 obj\n<<\n/Filter [ /ASCII85Decode /FlateDecode ] /Length 114\n>>\nstream\nGapQh0E=F,0U\\H3T\\pNYT^QKk?tc>IP,;W#U1^23ihPEM_?CW4KISi::p;W-:^G0Ccu@*&0$R,8/'1j`8Q@/e.SWW0e5Q^q;@(YOku$@?!6%nQ)u~>endstream\nendobj\nxref\n0 8\n0000000000 65535 f \n0000000061 00000 n \n0000000092 00000 n \n0000000199 00000 n \n0000000402 00000 n \n0000000470 00000 n \n0000000731 00000 n \n0000000790 00000 n \ntrailer\n<<\n/ID \n[<e3c564374ff070f36f1213b0fb8d46a5><e3c564374ff070f36f1213b0fb8d46a5>]\n% ReportLab generated PDF document -- digest (opensource)\n\n/Info 5 0 R\n/Root 4 0 R\n/Size 8\n>>\nstartxref\n994\n%%EOF\n"

import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from modulo_auditoria.models.auditoria import Auditoria
from modulo_casos.models.caso import Caso
from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.models.jerarquia import jerarquia as Jerarquia
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho
from modulo_catalogo.serializers.carga_pdf_serializer import CargaArticulosPDFSerializer
from modulo_clientes.models.cliente import Cliente
from modulo_ia.models.chunk import ChunkCaso
from modulo_ia.models.embedding import EmbeddingArticulo, EmbeddingChunk
from modulo_ia.services.ranking_service import RankingService
from modulo_usuarios.tests.factories import crear_rol, crear_usuario

URL_NORMAS = "/api/catalogo/normas/"
URL_ARTICULOS = "/api/catalogo/articulos/"


def _url_detalle(norma):
    return f"{URL_NORMAS}{norma.pk}/"


def _url_activar(norma):
    return f"{URL_NORMAS}{norma.pk}/activar/"


def _ids(response):
    """IDs de una respuesta de lista, paginada o no."""
    data = response.data
    items = data["results"] if isinstance(data, dict) and "results" in data else data
    return {item["id"] for item in items}


class NormaEliminacionApiTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario("admin.normas", rol=crear_rol("Administrador"))
        cls.abogado = crear_usuario("abogado.normas", rol=crear_rol("Abogado"))
        cls.rama = RamaDerecho.objects.create(nombre="Rama test normas")
        cls.jerarquia = Jerarquia.objects.create(nivel=98, nombre="Jerarquía test normas")

    def setUp(self):
        self.norma = Norma.objects.create(
            nombre="Código de prueba", sigla="CDP", jerarquia=self.jerarquia
        )
        self.articulo = Articulo.objects.create(
            numero_articulo="1", titulo="Art. 1", contenido="Contenido de prueba.",
            norma=self.norma, rama=self.rama,
        )
        self.client.force_authenticate(self.admin)

    # ------------------------------------------------------------------
    # Eliminar
    # ------------------------------------------------------------------

    def test_eliminar_marca_la_norma_como_inactiva_sin_borrarla(self):
        resp = self.client.delete(_url_detalle(self.norma))

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.norma.refresh_from_db()
        self.assertFalse(self.norma.estado)
        self.assertTrue(Norma.objects.filter(pk=self.norma.pk).exists())

    def test_eliminar_no_toca_los_articulos(self):
        self.client.delete(_url_detalle(self.norma))

        self.articulo.refresh_from_db()
        self.assertTrue(self.articulo.estado)

    def test_eliminar_registra_auditoria(self):
        self.client.delete(_url_detalle(self.norma))

        self.assertTrue(
            Auditoria.objects.filter(
                tabla="normas", accion="DELETE", registro_id=self.norma.pk
            ).exists()
        )

    def test_la_norma_eliminada_sale_de_la_lista_por_defecto(self):
        self.client.delete(_url_detalle(self.norma))

        resp = self.client.get(URL_NORMAS)
        self.assertNotIn(self.norma.pk, _ids(resp))

        resp = self.client.get(f"{URL_NORMAS}lista/")
        self.assertNotIn(self.norma.pk, _ids(resp))

    def test_admin_ve_las_eliminadas_con_estado_false(self):
        self.client.delete(_url_detalle(self.norma))

        resp = self.client.get(URL_NORMAS, {"estado": "false"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn(self.norma.pk, _ids(resp))

        resp = self.client.get(URL_NORMAS, {"estado": "true"})
        self.assertNotIn(self.norma.pk, _ids(resp))

    def test_eliminar_una_norma_ya_eliminada_da_400(self):
        self.client.delete(_url_detalle(self.norma))

        resp = self.client.delete(_url_detalle(self.norma))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            Auditoria.objects.filter(tabla="normas", accion="DELETE").count(), 1
        )

    def test_los_articulos_de_una_norma_eliminada_dejan_de_verse(self):
        self.assertIn(self.articulo.pk, _ids(self.client.get(URL_ARTICULOS)))

        self.client.delete(_url_detalle(self.norma))

        self.assertNotIn(self.articulo.pk, _ids(self.client.get(URL_ARTICULOS)))

    # ------------------------------------------------------------------
    # Restaurar
    # ------------------------------------------------------------------

    def test_restaurar_reactiva_la_norma_y_sus_articulos_vuelven(self):
        self.client.delete(_url_detalle(self.norma))

        resp = self.client.post(_url_activar(self.norma))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.norma.refresh_from_db()
        self.assertTrue(self.norma.estado)
        self.assertIn(self.norma.pk, _ids(self.client.get(URL_NORMAS)))
        self.assertIn(self.articulo.pk, _ids(self.client.get(URL_ARTICULOS)))

    def test_restaurar_registra_auditoria(self):
        self.client.delete(_url_detalle(self.norma))
        self.client.post(_url_activar(self.norma))

        self.assertTrue(
            Auditoria.objects.filter(
                tabla="normas", accion="UPDATE", registro_id=self.norma.pk
            ).exists()
        )

    def test_restaurar_una_norma_activa_da_400(self):
        resp = self.client.post(_url_activar(self.norma))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_restaurar_con_otra_norma_activa_del_mismo_nombre_da_409(self):
        self.client.delete(_url_detalle(self.norma))
        # Mientras estaba eliminada se cargó otra con el mismo nombre.
        otra = Norma.objects.create(nombre="CÓDIGO DE PRUEBA", sigla="OTRA")

        resp = self.client.post(_url_activar(self.norma))

        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(resp.data["existente"]["id"], otra.pk)
        self.norma.refresh_from_db()
        self.assertFalse(self.norma.estado)

    def test_restaurar_con_otra_norma_activa_de_la_misma_sigla_da_409(self):
        self.client.delete(_url_detalle(self.norma))
        Norma.objects.create(nombre="Un nombre totalmente distinto", sigla="cdp")

        resp = self.client.post(_url_activar(self.norma))

        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_restaurar_una_norma_inexistente_da_404(self):
        resp = self.client.post(f"{URL_NORMAS}999999/activar/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------
    # Permisos y campo estado
    # ------------------------------------------------------------------

    def test_abogado_no_puede_eliminar_ni_restaurar(self):
        self.client.force_authenticate(self.abogado)

        resp = self.client.delete(_url_detalle(self.norma))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        Norma.objects.filter(pk=self.norma.pk).update(estado=False)
        resp = self.client.post(_url_activar(self.norma))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.norma.refresh_from_db()
        self.assertFalse(self.norma.estado)

    def test_abogado_no_ve_normas_eliminadas_ni_con_estado_false(self):
        self.client.delete(_url_detalle(self.norma))
        self.client.force_authenticate(self.abogado)

        resp = self.client.get(URL_NORMAS, {"estado": "false"})
        self.assertNotIn(self.norma.pk, _ids(resp))

        resp = self.client.get(_url_detalle(self.norma))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_el_estado_no_se_puede_cambiar_por_patch(self):
        resp = self.client.patch(_url_detalle(self.norma), {"estado": False}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.norma.refresh_from_db()
        self.assertTrue(self.norma.estado)


class CargaPdfNormaEliminadaTests(TestCase):
    """La carga de PDF no debe duplicar una norma que existe pero está eliminada."""

    @classmethod
    def setUpTestData(cls):
        cls.rama = RamaDerecho.objects.create(nombre="Rama test carga")

    def _datos(self, **extra):
        pdf = SimpleUploadedFile("norma.pdf", PDF_MINIMO_1_PAGINA, content_type="application/pdf")
        return {"archivo": pdf, "rama_id": self.rama.pk, **extra}

    def test_rechaza_el_nombre_de_una_norma_eliminada(self):
        Norma.objects.create(nombre="Ley de prueba eliminada", sigla="LPE", estado=False)
        antes = Norma.objects.count()

        serializer = CargaArticulosPDFSerializer(
            data=self._datos(nombre_documento="LEY DE PRUEBA ELIMINADA")
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("nombre_documento", serializer.errors)
        self.assertEqual(Norma.objects.count(), antes)

    def test_rechaza_la_sigla_de_una_norma_eliminada(self):
        Norma.objects.create(nombre="Ley de prueba eliminada", sigla="LPE", estado=False)
        antes = Norma.objects.count()

        serializer = CargaArticulosPDFSerializer(
            data=self._datos(nombre_documento="Otro nombre cualquiera", sigla="lpe")
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(Norma.objects.count(), antes)

    def test_una_norma_nueva_se_sigue_creando_normalmente(self):
        serializer = CargaArticulosPDFSerializer(
            data=self._datos(nombre_documento="Código de Comercio")
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertTrue(Norma.objects.filter(nombre="Código de Comercio", estado=True).exists())


def _vector(bloque, dim=768, n_bloques=3, seed=0):
    rng = np.random.default_rng(seed)
    v = np.zeros(dim)
    ancho = dim // n_bloques
    v[bloque * ancho:(bloque + 1) * ancho] = rng.normal(size=ancho)
    return (v / np.linalg.norm(v)).tolist()


class RankingIgnoraNormasEliminadasTests(TestCase):
    """Los artículos de una norma eliminada no deben entrar al ranking del análisis."""

    @classmethod
    def setUpTestData(cls):
        rol = crear_rol("Abogado")
        cls.usuario = crear_usuario("ranking.normas", rol=rol)
        cls.cliente = Cliente.objects.create(nombres="Cliente", apellidos="Test")
        cls.rama = RamaDerecho.objects.create(nombre="Rama test ranking normas")
        jerarquia = Jerarquia.objects.create(nivel=97, nombre="Jerarquía ranking normas")
        cls.norma_activa = Norma.objects.create(nombre="Norma activa ranking", jerarquia=jerarquia)
        cls.norma_eliminada = Norma.objects.create(nombre="Norma eliminada ranking", jerarquia=jerarquia)

        cls.vector = _vector(0, seed=1)
        cls.art_activo = Articulo.objects.create(
            numero_articulo="A-1", titulo="Art. A-1", contenido="Robo de bien mueble.",
            norma=cls.norma_activa, rama=cls.rama,
        )
        cls.art_eliminado = Articulo.objects.create(
            numero_articulo="B-1", titulo="Art. B-1", contenido="Robo de bien mueble.",
            norma=cls.norma_eliminada, rama=cls.rama,
        )
        EmbeddingArticulo.objects.create(articulo=cls.art_activo, vector=cls.vector)
        EmbeddingArticulo.objects.create(articulo=cls.art_eliminado, vector=cls.vector)

    def _caso(self):
        caso = Caso.objects.create(
            codigo="CASO-NORMA-ELIMINADA", titulo="Caso", descripcion="",
            usuario=self.usuario, cliente=self.cliente, rama_detectada=self.rama,
        )
        chunk = ChunkCaso.objects.create(caso=caso, contenido="robo", orden=1, tipo="texto")
        EmbeddingChunk.objects.create(chunk=chunk, vector=self.vector)
        return caso

    def test_el_articulo_de_una_norma_eliminada_no_entra_al_ranking(self):
        Norma.objects.filter(pk=self.norma_eliminada.pk).update(estado=False)

        resultados = RankingService.calcular_ranking(self._caso())
        articulos = {r.articulo_id for r in resultados}

        self.assertIn(self.art_activo.pk, articulos)
        self.assertNotIn(self.art_eliminado.pk, articulos)

    def test_al_restaurar_la_norma_sus_articulos_vuelven_al_ranking(self):
        Norma.objects.filter(pk=self.norma_eliminada.pk).update(estado=False)
        Norma.objects.filter(pk=self.norma_eliminada.pk).update(estado=True)

        resultados = RankingService.calcular_ranking(self._caso())
        articulos = {r.articulo_id for r in resultados}

        self.assertIn(self.art_eliminado.pk, articulos)
