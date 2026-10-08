import io
import tempfile
from unittest.mock import patch

from django.test import TestCase, override_settings
from pypdf import PdfWriter

from modulo_documentos.models.documento import DocumentoCaso, TipoDoc, TextoDocumentoCaso
from modulo_documentos.services.extraccion_texto_service import ExtraccionTextoService
from modulo_ia.services.chunking_service import ChunkingService
from modulo_casos.models.caso import Caso
from modulo_clientes.models.cliente import Cliente
from modulo_usuarios.tests.factories import crear_usuario, crear_rol


class ExtraccionTextoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuario = crear_usuario("extraccion.pdf", rol=crear_rol("Abogado"))
        cliente = Cliente.objects.create(nombres="Cliente", apellidos="PDF")
        cls.caso = Caso.objects.create(
            codigo="CASO-EXTRACCION", titulo="PDF", descripcion="Descripción de respaldo.",
            usuario=usuario, cliente=cliente,
        )
        cls.documento = DocumentoCaso.objects.create(
            caso=cls.caso, nombre_original="prueba.pdf", ruta_archivo="prueba.pdf",
            tipo_archivo="pdf", tamano=1, tipo_documento=TipoDoc.objects.create(tipo="prueba"),
        )

    def test_reutiliza_texto_y_invalida_cache_si_cambia_pdf(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as carpeta, override_settings(MEDIA_ROOT=carpeta):
            archivo = Path(carpeta) / "prueba.pdf"
            archivo.write_bytes(b"pdf-uno")
            with patch.object(ExtraccionTextoService, "paginas", return_value=["Texto jurídico."]) as extraer:
                self.assertEqual(ChunkingService._obtener_texto_y_tipo(self.caso), ("Texto jurídico.", "pdf"))
                ExtraccionTextoService.extraer_documento(self.documento)
                extraer.assert_called_once()
            archivo.write_bytes(b"pdf-dos")
            with patch.object(ExtraccionTextoService, "paginas", return_value=["Otro texto jurídico."]) as extraer:
                self.assertEqual(ExtraccionTextoService.extraer_documento(self.documento), "Otro texto jurídico.")
                extraer.assert_called_once()
            self.assertEqual(TextoDocumentoCaso.objects.count(), 1)

    def test_pdf_real_sin_texto_reutiliza_resultado_vacio_y_descripcion(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as carpeta, override_settings(MEDIA_ROOT=carpeta):
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            writer.write(str(Path(carpeta) / "prueba.pdf"))
            self.assertEqual(ChunkingService._obtener_texto_y_tipo(self.caso), (self.caso.descripcion, "texto"))
            with patch.object(ExtraccionTextoService, "paginas") as extraer:
                self.assertEqual(ExtraccionTextoService.extraer_documento(self.documento), "")
                extraer.assert_not_called()

    def test_extraccion_restaura_posicion_del_archivo(self):
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        archivo = io.BytesIO()
        writer.write(archivo)
        archivo.seek(5)
        self.assertEqual(ExtraccionTextoService.extraer(archivo), "")
        self.assertEqual(archivo.tell(), 5)

    def _pdf_mixto(self):
        import fitz
        pdf = fitz.open()
        pdf.new_page().insert_text((20, 30), 'Texto nativo que debe conservarse completo.')
        pagina = pdf.new_page()
        pagina.draw_rect(fitz.Rect(10, 10, 150, 100))
        contenido = pdf.tobytes()
        pdf.close()
        return io.BytesIO(contenido)

    def test_ocr_solo_en_paginas_sin_texto_y_conserva_el_orden(self):
        archivo = self._pdf_mixto()
        archivo.seek(4)
        with patch('modulo_catalogo.services.ocr_local_service.transcribir_pagina', return_value='Texto de la página escaneada.') as ocr:
            texto = ExtraccionTextoService.extraer(archivo)
        self.assertIn('Texto nativo', texto)
        self.assertTrue(texto.endswith('Texto de la página escaneada.'))
        self.assertEqual(ocr.call_args.args[1], 2)
        self.assertEqual(archivo.tell(), 4)

    def test_fallo_ocr_no_omite_silenciosamente_la_pagina(self):
        with patch('modulo_catalogo.services.ocr_local_service.transcribir_pagina', side_effect=ValueError('No se obtuvo texto legible de la página 2.')):
            with self.assertRaisesMessage(ValueError, 'No se pudo extraer el texto del PDF del caso'):
                ExtraccionTextoService.extraer(self._pdf_mixto())
