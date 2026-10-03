import hashlib
from unittest.mock import patch
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from modulo_catalogo.models import Norma, RamaDerecho, DocumentoOficial
from modulo_usuarios.tests.factories import crear_rol, crear_usuario
from .test_validacion_pdf_endpoints import PDF_MINIMO_1_PAGINA

class NormativaEndpointsTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.abogado = crear_usuario('normativa.abogado', rol=crear_rol('Abogado'))
        self.asistente = crear_usuario('normativa.asistente', rol=crear_rol('Asistente'))
        self.rama = RamaDerecho.objects.create(nombre='Rama normativa endpoint')
        self.client.force_authenticate(self.abogado)

    def archivo(self):
        return SimpleUploadedFile('ley.pdf', PDF_MINIMO_1_PAGINA, content_type='application/pdf')

    def test_estado_de_tarea_de_otro_usuario_no_se_expone(self):
        cache.set('tarea_normativa:ajena', {'usuario_id': self.asistente.pk, 'estado': 'SUCCESS', 'resultado': {'revision_token': 'privado'}})
        self.assertEqual(self.client.get('/api/catalogo/tareas-normativas/ajena/').status_code, 404)

    def test_estado_de_tarea_propia_devuelve_resultado(self):
        cache.set('tarea_normativa:propia', {'usuario_id': self.abogado.pk, 'estado': 'STARTED', 'resumen': {'paso': 'Leyendo'}})
        resp = self.client.get('/api/catalogo/tareas-normativas/propia/')
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('usuario_id', resp.data)

    def test_asistente_no_puede_iniciar_scraping_o_lectura(self):
        self.client.force_authenticate(self.asistente)
        self.assertEqual(self.client.post('/api/catalogo/gaceta/sincronizar/', {'max_paginas': 1}).status_code, 403)
        self.assertEqual(self.client.post('/api/catalogo/cargar-articulos/revisar-iniciar/', {}).status_code, 403)

    def test_abogado_no_puede_confirmar_afectacion_por_endpoint_admin(self):
        self.assertEqual(self.client.post('/api/catalogo/cambios-normativos/999/revisar/', {}).status_code, 403)

    def test_rango_de_fecha_invertido_no_inicia_scraping(self):
        resp = self.client.post('/api/catalogo/gaceta/sincronizar/', {'desde': '2026-10-03', 'hasta': '2026-01-01'}, format='json')
        self.assertEqual(resp.status_code, 400)

    @patch('modulo_catalogo.services.lectura_normativa_service.extraer_metadatos', return_value={'tipo_norma': 'Ley', 'numero_norma': '1773', 'fecha_norma': '2026-10-02'})
    @patch('modulo_catalogo.services.lectura_normativa_service.detectar_cambios', return_value=[])
    @patch('modulo_catalogo.services.pdf_normativo_service.leer_pdf', return_value=('ARTÍCULO 1. Texto de la norma principal suficiente.', []))
    @patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'unidades': []})
    def test_pdf_alterado_no_puede_presentarse_como_documento_oficial(self, *mocks):
        oficial = DocumentoOficial.objects.create(url_fuente='http://www.gacetaoficialdebolivia.gob.bo/normas/verGratis_gob/301978',
            url_pdf='http://www.gacetaoficialdebolivia.gob.bo/normas/descargarNrms/301978', identificador='301978', titulo='Ley 1773',
            tipo='Ley', numero='1773', estado_descarga='descargado', penal=True, hash_pdf='0'*64)
        resp = self.client.post('/api/catalogo/cargar-articulos/revisar/', {'archivo': self.archivo(), 'rama_id': self.rama.pk,
            'nombre_documento': 'Ley 1773', 'motor_lectura': 'qwen', 'documento_oficial_id': oficial.pk}, format='multipart')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('no coincide', str(resp.data))

    @patch('modulo_catalogo.views.revision_carga_view.extraer_texto_pdf_bytes', return_value='ARTÍCULO 1. Texto suficiente de la nueva norma.')
    @patch('modulo_catalogo.views.tareas_normativas_view.iniciar')
    def test_revision_asincrona_conserva_archivo_y_no_crea_norma(self, iniciar, texto):
        resultado = {}
        def ejecutar(usuario, trabajo, final=None):
            resultado.update(trabajo(lambda resumen: None)); return 'revision-test'
        iniciar.side_effect = ejecutar
        resp = self.client.post('/api/catalogo/cargar-articulos/revisar-iniciar/', {'archivo': self.archivo(),
            'rama_id': self.rama.pk, 'nombre_documento': 'Norma pendiente de revisión', 'motor_lectura': 'clasico'}, format='multipart')
        self.assertEqual(resp.status_code, 202, resp.data)
        self.assertTrue(resultado['revision_token'])
        self.assertEqual(len(resultado['articulos']), 1)
        self.assertFalse(Norma.objects.filter(nombre='Norma pendiente de revisión').exists())
