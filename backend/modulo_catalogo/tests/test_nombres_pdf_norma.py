from django.test import SimpleTestCase

from modulo_catalogo.views.carga_articulos_view import _nombre_pdf_norma


class NombrePDFNormaTests(SimpleTestCase):
    def test_usa_nombre_registrado_y_normaliza_acentos(self):
        self.assertEqual(_nombre_pdf_norma("Código de Procedimiento Penal"),
                         "codigo-de-procedimiento-penal.pdf")

    def test_limita_longitud_y_elimina_separadores_de_ruta(self):
        nombre = _nombre_pdf_norma("Ley / \\ : " + "Abreviación procesal penal " * 20)
        self.assertLessEqual(len(nombre), 64)
        self.assertNotIn("/", nombre)
        self.assertNotIn("\\", nombre)
        self.assertNotIn(":", nombre)
        self.assertTrue(nombre.endswith(".pdf"))

    def test_nombres_reservados_windows_y_nombre_vacio(self):
        self.assertEqual(_nombre_pdf_norma("CON"), "norma-con.pdf")
        self.assertEqual(_nombre_pdf_norma("LPT1"), "norma-lpt1.pdf")
        self.assertEqual(_nombre_pdf_norma("///"), "norma.pdf")


class GuardadoNombrePDFTests(SimpleTestCase):
    def test_guardado_usa_norma_y_conserva_archivos_en_cargas_repetidas(self):
        import os
        import tempfile
        from types import SimpleNamespace
        from unittest.mock import patch
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        from modulo_catalogo.views.carga_articulos_view import CargaArticulosView

        norma = SimpleNamespace(pk=5, id=5, nombre="Ley 1173", sigla="LEY 1173")
        rama = SimpleNamespace(id=1, nombre="Penal")
        request = SimpleNamespace(data={}, user=SimpleNamespace(id=1, usuario="prueba"))
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media), \
                patch("modulo_catalogo.views.carga_articulos_view.CargaArticulosPDFSerializer") as serializer, \
                patch("modulo_catalogo.views.carga_articulos_view.DocumentoNorma.objects.create") as crear, \
                patch("modulo_catalogo.views.carga_articulos_view.lanzar_carga_en_background", return_value="tarea"), \
                patch("modulo_catalogo.views.carga_articulos_view.registrar_auditoria"):
            serializer.return_value.is_valid.return_value = True
            serializer.return_value.context = {}
            crear.return_value = SimpleNamespace(pk=1, id=1)
            rutas = []
            for contenido in (b"primer PDF", b"segundo PDF"):
                serializer.return_value.validated_data = {
                    "archivo": SimpleUploadedFile("nombre-original-muy-largo.pdf", contenido),
                    "norma": norma, "rama": rama,
                }
                respuesta = CargaArticulosView().post(request)
                self.assertEqual(respuesta.status_code, 202, respuesta.data)
                ruta = crear.call_args.kwargs["ruta_archivo"]
                rutas.append(os.path.join(media, ruta))
            self.assertEqual(os.path.basename(rutas[0]), "ley-1173.pdf")
            self.assertNotEqual(rutas[0], rutas[1])
            for ruta, esperado in zip(rutas, (b"primer PDF", b"segundo PDF")):
                with open(ruta, "rb") as archivo:
                    self.assertEqual(archivo.read(), esperado)
