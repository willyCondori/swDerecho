"""
Tests de las cargas de PDF en curso: el índice de cargas activas
(background_tasks.listar_cargas_activas) y el endpoint
GET /api/catalogo/cargar-articulos/activas/, que permite retomar la vista
de progreso cuando el usuario sale de la pantalla de carga y vuelve a entrar.
"""

# PDF mínimo (una página en blanco) para pasar la validación real del
# contenido, que ahora abre el archivo con pypdf.
PDF_MINIMO_1_PAGINA = b"%PDF-1.3\n%\x93\x8c\x8b\x9e ReportLab Generated PDF document (opensource)\n1 0 obj\n<<\n/F1 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/BaseFont /Helvetica /Encoding /WinAnsiEncoding /Name /F1 /Subtype /Type1 /Type /Font\n>>\nendobj\n3 0 obj\n<<\n/Contents 7 0 R /MediaBox [ 0 0 595.2756 841.8898 ] /Parent 6 0 R /Resources <<\n/Font 1 0 R /ProcSet [ /PDF /Text /ImageB /ImageC /ImageI ]\n>> /Rotate 0 /Trans <<\n\n>> \n  /Type /Page\n>>\nendobj\n4 0 obj\n<<\n/PageMode /UseNone /Pages 6 0 R /Type /Catalog\n>>\nendobj\n5 0 obj\n<<\n/Author (anonymous) /CreationDate (D:20260922030645+00'00') /Creator (anonymous) /Keywords () /ModDate (D:20260922030645+00'00') /Producer (ReportLab PDF Library - \\(opensource\\)) \n  /Subject (unspecified) /Title (untitled) /Trapped /False\n>>\nendobj\n6 0 obj\n<<\n/Count 1 /Kids [ 3 0 R ] /Type /Pages\n>>\nendobj\n7 0 obj\n<<\n/Filter [ /ASCII85Decode /FlateDecode ] /Length 114\n>>\nstream\nGapQh0E=F,0U\\H3T\\pNYT^QKk?tc>IP,;W#U1^23ihPEM_?CW4KISi::p;W-:^G0Ccu@*&0$R,8/'1j`8Q@/e.SWW0e5Q^q;@(YOku$@?!6%nQ)u~>endstream\nendobj\nxref\n0 8\n0000000000 65535 f \n0000000061 00000 n \n0000000092 00000 n \n0000000199 00000 n \n0000000402 00000 n \n0000000470 00000 n \n0000000731 00000 n \n0000000790 00000 n \ntrailer\n<<\n/ID \n[<e3c564374ff070f36f1213b0fb8d46a5><e3c564374ff070f36f1213b0fb8d46a5>]\n% ReportLab generated PDF document -- digest (opensource)\n\n/Info 5 0 R\n/Root 4 0 R\n/Size 8\n>>\nstartxref\n994\n%%EOF\n"

import shutil
import tempfile
import threading
import time
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from modulo_catalogo.models.rama import RamaDerecho
from modulo_catalogo.services import background_tasks
from modulo_catalogo.services.background_tasks import (
    _registrar_en_indice,
    lanzar_carga_en_background,
    listar_cargas_activas,
    obtener_progreso,
)
from modulo_usuarios.tests.factories import crear_perfil, crear_rol, crear_usuario

CARGAR_FN = "modulo_catalogo.services.carga_pdf_service.cargar_articulos_desde_bytes"


class ResultadoFalso:
    def resumen(self):
        return {"insertados": 3}


class CargaFalsa:
    """
    Reemplaza a cargar_articulos_desde_bytes: reporta progreso, avisa que
    arrancó y se queda esperando (sin tocar la BD) hasta que el test la suelte.
    """

    def __init__(self, falla=False):
        self.arranco = threading.Event()
        self.soltar = threading.Event()
        self.falla = falla

    def __call__(self, *, contenido_pdf, norma_id, rama_id, jerarquia_id, task, sobrescribir):
        task.update_state(state="STARTED", meta={"progreso": 42, "paso": "Procesando artículo 5/10..."})
        self.arranco.set()
        self.soltar.wait(timeout=10)
        if self.falla:
            raise RuntimeError("PDF ilegible")
        return ResultadoFalso()


def esperar(condicion, timeout=5):
    limite = time.time() + timeout
    while time.time() < limite:
        if condicion():
            return True
        time.sleep(0.02)
    return False


class CargasActivasBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.abogado = crear_usuario(usuario="abogado1", rol=crear_rol("Abogado"))
        crear_perfil(cls.abogado, email="abogado1@example.com", nombres="Laura", apellidos="Quispe")
        cls.admin = crear_usuario(usuario="admin1", rol=crear_rol("Administrador"))

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def lanzar(self, carga, **info):
        with patch(CARGAR_FN, carga):
            task_id = lanzar_carga_en_background(
                contenido_pdf=b"%PDF-1.4", norma_id=1, rama_id=1,
                info={"nombre_documento": "Código Penal", "archivo": "cp.pdf", **info},
            )
            self.addCleanup(carga.soltar.set)
            self.assertTrue(carga.arranco.wait(timeout=5))
        return task_id

    def activas(self, usuario=None):
        self.client.force_authenticate(usuario or self.abogado)
        return self.client.get(reverse("cargar-articulos-activas"))


class IndiceDeCargasActivasTests(CargasActivasBase):
    def test_sin_cargas_devuelve_lista_vacia(self):
        self.assertEqual(listar_cargas_activas(), [])
        r = self.activas()
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data, [])

    def test_carga_en_curso_aparece_con_su_progreso_y_desaparece_al_terminar(self):
        carga = CargaFalsa()
        task_id = self.lanzar(carga, usuario_id=self.abogado.id, usuario_nombre="Laura Quispe")

        r = self.activas()
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)
        fila = r.data[0]
        self.assertEqual(fila["task_id"], task_id)
        self.assertEqual(fila["estado"], "STARTED")
        self.assertEqual(fila["progreso"], 42)
        self.assertEqual(fila["paso"], "Procesando artículo 5/10...")
        self.assertEqual(fila["nombre_documento"], "Código Penal")
        self.assertEqual(fila["archivo"], "cp.pdf")
        self.assertEqual(fila["usuario_nombre"], "Laura Quispe")
        self.assertIn("iniciada_at", fila)
        self.assertNotIn("usuario_id", fila)

        carga.soltar.set()
        self.assertTrue(esperar(lambda: obtener_progreso(task_id)["state"] == "SUCCESS"))
        self.assertEqual(self.activas().data, [])
        # El resultado sigue disponible por task_id, como antes.
        self.assertEqual(obtener_progreso(task_id)["meta"]["resumen"], {"insertados": 3})

    def test_carga_que_falla_sale_de_las_activas(self):
        carga = CargaFalsa(falla=True)
        task_id = self.lanzar(carga)
        self.assertEqual(len(self.activas().data), 1)

        carga.soltar.set()
        self.assertTrue(esperar(lambda: obtener_progreso(task_id)["state"] == "FAILURE"))
        self.assertEqual(self.activas().data, [])
        self.assertEqual(obtener_progreso(task_id)["meta"]["error"], "PDF ilegible")

    def test_es_mia_distingue_al_usuario_que_la_inicio(self):
        self.lanzar(CargaFalsa(), usuario_id=self.abogado.id)
        self.assertTrue(self.activas(self.abogado).data[0]["es_mia"])
        self.assertFalse(self.activas(self.admin).data[0]["es_mia"])

    def test_la_mas_reciente_va_primero(self):
        primera = self.lanzar(CargaFalsa(), nombre_documento="Primera")
        segunda = self.lanzar(CargaFalsa(), nombre_documento="Segunda")
        ids = [c["task_id"] for c in self.activas().data]
        self.assertEqual(ids, [segunda, primera])

    def test_entrada_sin_progreso_en_cache_se_limpia_del_indice(self):
        _registrar_en_indice("fantasma", {"nombre_documento": "X", "iniciada_at": "2026-01-01T00:00:00+00:00"})
        self.assertEqual(listar_cargas_activas(), [])
        self.assertNotIn("fantasma", cache.get(background_tasks.INDICE_KEY))

    def test_requiere_autenticacion(self):
        r = self.client.get(reverse("cargar-articulos-activas"))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class PostRegistraDatosDeLaCargaTests(CargasActivasBase):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.rama = RamaDerecho.objects.create(nombre="Penal")

    def test_post_pasa_a_la_carga_los_datos_del_documento_y_del_usuario(self):
        self.client.force_authenticate(self.abogado)
        with override_settings(MEDIA_ROOT=self.media), patch(
            "modulo_catalogo.views.carga_articulos_view.lanzar_carga_en_background",
            return_value="task-123",
        ) as lanzar:
            r = self.client.post(
                "/api/catalogo/cargar-articulos/",
                {
                    "archivo": SimpleUploadedFile("cpp.pdf", PDF_MINIMO_1_PAGINA, content_type="application/pdf"),
                    "nombre_documento": "Código de Procedimiento Penal",
                    "rama_id": self.rama.id,
                },
                format="multipart",
            )
        self.assertEqual(r.status_code, status.HTTP_202_ACCEPTED, r.data)
        self.assertEqual(r.data["task_id"], "task-123")
        info = lanzar.call_args.kwargs["info"]
        self.assertEqual(info["nombre_documento"], "Código de Procedimiento Penal")
        self.assertEqual(info["archivo"], "cpp.pdf")
        self.assertEqual(info["rama"], "Penal")
        self.assertEqual(info["usuario_id"], self.abogado.id)
        self.assertEqual(info["usuario_nombre"], "Laura Quispe")
