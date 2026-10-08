from importlib import import_module
from types import SimpleNamespace
from django.apps import apps
from django.db import connection
from django.test import TestCase
from modulo_catalogo.models import DocumentoNorma, Norma


class RutasDocumentosTests(TestCase):
    def test_normaliza_ruta_windows_sin_cambiar_documento_y_es_idempotente(self):
        norma = Norma.objects.create(nombre='Prueba rutas')
        documento = DocumentoNorma.objects.create(norma=norma, nombre_original='Ley.pdf',
            ruta_archivo=r'documentos_normativas\ley\Ley.pdf', tamano=42)
        normalizar = import_module('modulo_catalogo.migrations.0019_rutas_portables_documentos').normalizar_rutas
        for _ in range(2):
            normalizar(apps, SimpleNamespace(connection=connection))
        documento.refresh_from_db()
        self.assertEqual(documento.ruta_archivo, 'documentos_normativas/ley/Ley.pdf')
        self.assertEqual(documento.tamano, 42)
        self.assertEqual(documento.nombre_original, 'Ley.pdf')
        self.assertEqual(documento.norma_id, norma.pk)
