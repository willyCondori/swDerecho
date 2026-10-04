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


    @patch('modulo_catalogo.services.lectura_normativa_service.consultar', side_effect=AssertionError('No usar Qwen'))
    @patch('modulo_catalogo.services.pdf_normativo_service.leer_pdf')
    def test_compilacion_se_revisa_sin_cortar_pdf_y_cada_norma_tiene_su_revision(self, lectura, modelo):
        texto = 'LEY N° 100\nLEY DE 10 DE ENERO DE 2000\nARTÍCULO 1. Contenido de la ley principal.\nLEY N° 200\nLEY DE 20 DE ENERO DE 2001\nARTÍCULO 1. Contenido distinto de otra ley.'
        lectura.return_value = (texto, [])
        parametros = {'archivo': self.archivo(), 'rama_id': self.rama.pk,
                      'nombre_documento': 'Ley 100', 'motor_lectura': 'clasico'}
        principal = self.client.post('/api/catalogo/cargar-articulos/revisar/', parametros, format='multipart')
        self.assertEqual(principal.status_code, 200, principal.data)
        self.assertEqual(len(principal.data['secciones_documento']), 2)
        self.assertIn('ley principal', principal.data['articulos'][0]['texto_nuevo'])
        self.assertNotIn('otra ley', principal.data['articulos'][0]['texto_nuevo'])
        anexo = self.client.post('/api/catalogo/cargar-articulos/revisar/',
            {**parametros, 'archivo': self.archivo(), 'seccion_documento': '1', 'nombre_documento': 'Ley 200'}, format='multipart')
        self.assertEqual(anexo.status_code, 200, anexo.data)
        self.assertIn('otra ley', anexo.data['articulos'][0]['texto_nuevo'])
        self.assertEqual(anexo.data['metadatos']['numero_norma'], '200')
        self.assertNotEqual(principal.data['revision_token'], anexo.data['revision_token'])
        modelo.assert_not_called()

    @patch('modulo_catalogo.services.pdf_normativo_service.leer_pdf', return_value=('ARTÍCULO 1. Base.', []))
    @patch('modulo_catalogo.services.lectura_normativa_service.extraer_unidades')
    def test_alternativas_no_se_importan_hasta_elegir_y_no_permiten_reemplazo_completo(self, unidades, lectura):
        unidades.return_value = [
            {'numero': '1', 'texto': 'ARTÍCULO 1. Versión anterior.', 'titulo': 'Anterior'},
            {'numero': '1', 'texto': 'ARTÍCULO 1. Versión nueva.', 'titulo': 'Nueva'},
            {'numero': '2', 'texto': 'ARTÍCULO 2. Unidad inequívoca.', 'titulo': 'Dos'}]
        parametros = {'archivo': self.archivo(), 'rama_id': self.rama.pk,
                      'nombre_documento': 'Ley 100', 'motor_lectura': 'clasico'}
        resp = self.client.post('/api/catalogo/cargar-articulos/revisar/', parametros, format='multipart')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual([u['numero'] for u in resp.data['articulos']], ['2'])
        grupo = resp.data['unidades_ambiguas'][0]
        cache_revision = cache.get('revision_carga_pdf:' + resp.data['revision_token'])
        self.assertTrue(cache_revision['ambiguedades_pendientes'])
        from modulo_catalogo.views.revision_carga_view import validar_revision, datos_destino
        from rest_framework.exceptions import ValidationError
        datos = {'archivo': self.archivo(), 'rama': self.rama, 'nombre_documento': 'Ley 100',
                 'motor_lectura': 'clasico', 'revision_token': resp.data['revision_token'], 'modo_actualizacion': 'completo'}
        # El destino normalizado incluye los defaults del serializer.
        datos['variantes_unidades'] = {}
        with self.assertRaisesMessage(ValidationError, 'alternativas'):
            validar_revision(datos, self.abogado.pk)
        import json
        parametros['archivo'] = self.archivo()
        parametros['variantes_unidades'] = json.dumps({grupo['clave']: grupo['alternativas'][1]['id_unidad']})
        elegido = self.client.post('/api/catalogo/cargar-articulos/revisar/', parametros, format='multipart')
        self.assertEqual(elegido.status_code, 200, elegido.data)
        self.assertIn('Versión nueva', elegido.data['articulos'][0]['texto_nuevo'])
        self.assertFalse(cache.get('revision_carga_pdf:' + elegido.data['revision_token'])['ambiguedades_pendientes'])

    @patch('modulo_catalogo.services.pdf_normativo_service.leer_pdf')
    def test_extracto_anexo_impide_reemplazar_norma_completa(self, lectura):
        from modulo_catalogo.serializers.carga_pdf_serializer import CargaArticulosPDFSerializer
        from modulo_catalogo.views.revision_carga_view import validar_revision
        from rest_framework.exceptions import ValidationError
        lectura.return_value = ('LEY N° 100\nARTÍCULO 1. Objeto de norma principal.\nLEY N° 1333\nARTÍCULO 104. Delito ambiental.', [])
        parametros = {'archivo': self.archivo(), 'rama_id': self.rama.pk, 'nombre_documento': 'Ley 1333', 'motor_lectura': 'clasico', 'seccion_documento': '1'}
        resp = self.client.post('/api/catalogo/cargar-articulos/revisar/', parametros, format='multipart')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(resp.data['fragmento_normativo'])
        parametros.update(archivo=self.archivo(), revision_token=resp.data['revision_token'], modo_actualizacion='completo')
        serializer = CargaArticulosPDFSerializer(data=parametros, context={'solo_revision': True})
        serializer.is_valid(raise_exception=True)
        with self.assertRaisesMessage(ValidationError, 'extracto'):
            validar_revision(serializer.validated_data, self.abogado.pk)

    @patch('modulo_catalogo.services.pdf_normativo_service.leer_pdf')
    def test_extracto_modificatorio_requiere_identificar_norma_destinataria(self, lectura):
        import json
        lectura.return_value = ('LEY N° 100\nARTÍCULO 1. Objeto principal.\nLEY N° 1582\nMODIFICACIÓN DE LA LEY DE PENSIONES\nARTÍCULO 119. Delito de pensiones.', [])
        parametros = {'archivo': self.archivo(), 'rama_id': self.rama.pk, 'nombre_documento': 'Ley 1582', 'motor_lectura': 'clasico', 'seccion_documento': '1'}
        resp = self.client.post('/api/catalogo/cargar-articulos/revisar/', parametros, format='multipart')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(resp.data['identidad_por_verificar'])
        parametros.update(archivo=self.archivo(), nombre_documento='Ley de Pensiones', metadatos=json.dumps({'tipo_norma': 'Ley', 'numero_norma': '065', 'fecha_norma': '2010-12-10'}))
        resp = self.client.post('/api/catalogo/cargar-articulos/revisar/', parametros, format='multipart')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertFalse(resp.data['identidad_por_verificar'])
        self.assertEqual(resp.data['metadatos']['numero_norma'], '065')
        self.assertEqual(resp.data['seccion_activa'], '1')

    def test_lista_normas_devuelve_ramas_asociadas_sin_duplicar(self):
        from modulo_catalogo.models import Articulo
        norma = Norma.objects.create(nombre='Norma con rama asociada')
        Articulo.objects.create(norma=norma, rama=self.rama, numero_articulo='1', contenido='Texto primero')
        Articulo.objects.create(norma=norma, rama=self.rama, numero_articulo='2', contenido='Texto segundo')
        resp = self.client.get('/api/catalogo/normas/lista/')
        self.assertEqual(resp.status_code, 200)
        dato = next(n for n in resp.data if n['id'] == norma.pk)
        self.assertEqual(dato['ramas'], [{'id': self.rama.pk, 'nombre': self.rama.nombre}])
