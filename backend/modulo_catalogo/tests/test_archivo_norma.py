import os
import tempfile
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from modulo_catalogo.services.archivo_norma_service import guardar_pdf_norma


class ArchivoNormaTests(SimpleTestCase):
    @patch('modulo_catalogo.services.archivo_norma_service.timezone.now', return_value=datetime(2026, 10, 8, 2, 0, tzinfo=timezone.utc))
    def test_fecha_boliviana_nombre_bd_y_fisico_sin_sobrescribir(self, _):
        norma = SimpleNamespace(pk=5, nombre='Protección de los niños', sigla='')
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            first = guardar_pdf_norma(SimpleUploadedFile('ley_548.pdf', b'primero'), norma)
            second = guardar_pdf_norma(SimpleUploadedFile('otro.pdf', b'segundo'), norma)
            self.assertEqual(first['nombre'], 'Protección de los niños - 2026-10-07.pdf')
            self.assertEqual(second['nombre'], 'Protección de los niños - 2026-10-07 (2).pdf')
            self.assertEqual(os.path.basename(first['ruta_relativa']), first['nombre'])
            self.assertNotIn('\\', first['ruta_relativa'])
            with open(first['ruta'], 'rb') as stream:
                self.assertEqual(stream.read(), b'primero')
            self.assertEqual(first['metadatos']['nombre_archivo_subido'], 'ley_548.pdf')

    def test_sanea_caracteres_no_admitidos_sin_salir_de_la_carpeta(self):
        norma = SimpleNamespace(pk=6, nombre='../Ley: Protección / \"niños\"?', sigla='')
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            saved = guardar_pdf_norma(SimpleUploadedFile('original.pdf', b'pdf'), norma)
            self.assertTrue(os.path.commonpath([media, saved['ruta']]) == media)
            self.assertNotIn('/', saved['nombre'])
            self.assertNotIn(':', saved['nombre'])
            self.assertTrue(saved['nombre'].endswith('.pdf'))
