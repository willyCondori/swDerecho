from unittest.mock import patch
from types import SimpleNamespace
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from modulo_catalogo.models import Norma, RamaDerecho, Articulo, DocumentoNorma
from modulo_catalogo.models.jerarquia import jerarquia
from modulo_catalogo.services.algoritmos_normativos_service import extraer_metadatos_literales
from modulo_catalogo.services.carga_compilacion_service import aplicar_compilacion, validar_anexos
from modulo_usuarios.tests.factories import crear_usuario, crear_rol
from .test_validacion_pdf_endpoints import PDF_MINIMO_1_PAGINA

TEXTO = 'LEY N° 900\nARTÍCULO 1. Texto de la norma principal suficientemente largo.\nLEY N° 1333\nARTÍCULO 104. Delito ambiental suficientemente descrito.\nARTÍCULO 105. Segundo delito ambiental suficientemente descrito.'

class CargaCompilacionTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.usuario = crear_usuario('compilacion.abogado', rol=crear_rol('Abogado'))
        self.client.force_authenticate(self.usuario)
        self.rama = RamaDerecho.objects.create(nombre='Penal lote')
        self.tipo, _ = jerarquia.objects.get_or_create(
            nombre='Ley compilación pruebas', defaults={'nivel': 2, 'estado': True})
        self.principal = Norma.objects.create(nombre='Ley 900 principal', tipo_norma='Ley', numero_norma='900', jerarquia=self.tipo)

    def revisar(self, motor='clasico', texto=TEXTO, **extra):
        with patch('modulo_catalogo.services.pdf_normativo_service.leer_pdf', return_value=(texto, [])), patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'unidades': [], 'cambios': []}), patch('modulo_catalogo.services.lectura_normativa_service.extraer_metadatos', side_effect=extraer_metadatos_literales), patch('modulo_catalogo.services.compilaciones_service.segmentar_normas', wraps=__import__('modulo_catalogo.services.compilaciones_service', fromlist=['segmentar_normas']).segmentar_normas) as segmentar:
            # Ambos motores comparten aquí límites contrastados, sin Ollama real.
            original = segmentar._mock_wraps
            segmentar.side_effect = lambda texto, progreso=None, motor='clasico': original(texto, progreso, 'clasico')
            resp = self.client.post('/api/catalogo/cargar-articulos/revisar/', {
                'archivo': SimpleUploadedFile('compilacion.pdf', PDF_MINIMO_1_PAGINA, content_type='application/pdf'),
                'norma_id': self.principal.pk, 'rama_id': self.rama.pk, 'jerarquia_id': self.tipo.pk,
                'motor_lectura': motor, 'incluir_anexos': True, **extra}, format='multipart')
        self.assertEqual(resp.status_code, 200, resp.data)
        return resp.data, cache.get('revision_carga_pdf:' + resp.data['revision_token'])

    def fuente(self, plan):
        return DocumentoNorma.objects.create(norma=self.principal, rama=self.rama, nombre_original='compilacion.pdf', ruta_archivo='lote/compilacion.pdf', tamano=100,
            analisis_normativo={'secciones': plan['secciones'], 'cambios': plan['cambios']}, metadatos=plan['metadatos'])

    def cargar(self, plan):
        fuente = self.fuente(plan)
        with patch('modulo_catalogo.services.carga_pdf_service._obtener_modelo'), patch('modulo_ia.services.vectorizacion_service.vectorizar_textos', side_effect=lambda textos, modelo: [[0.1] * 768 for _ in textos]):
            return aplicar_compilacion(self.principal, self.rama, plan, 'articulos', ['1'], fuente.pk)

    def test_ambos_motores_revisan_anexos_sin_crear_normas(self):
        for motor in ['clasico', 'qwen']:
            respuesta, plan = self.revisar(motor)
            self.assertEqual(len(respuesta['anexos']), 1)
            self.assertEqual(respuesta['anexos'][0]['metadatos']['numero_norma'], '1333')
            self.assertEqual([a['numero'] for a in plan['anexos'][0]['articulos']], ['104', '105'])
            self.assertFalse(Norma.objects.filter(numero_norma='1333').exists())

    def test_carga_todas_las_normas_separadas_y_cuenta_creadas(self):
        _, plan = self.revisar()
        resultado = self.cargar(plan)
        norma = Norma.objects.get(numero_norma='1333')
        self.assertEqual(set(Articulo.objects.filter(norma=norma).values_list('numero_articulo', flat=True)), {'104', '105'})
        self.assertEqual(resultado.guardados, 3)
        self.assertEqual(resultado.revision['normas_guardadas'], 2)
        self.assertEqual(resultado.revision['normas_detectadas'], 2)
        self.assertEqual(resultado.revision['normas_creadas'], [{'id': norma.pk, 'nombre': 'LEY N° 1333'}])
        self.assertEqual(DocumentoNorma.objects.get(norma=norma).ruta_archivo, 'lote/compilacion.pdf')

    def test_reutiliza_norma_existente_y_conserva_articulos_ausentes(self):
        norma = Norma.objects.create(nombre='Ley del Medio Ambiente', tipo_norma='Ley', numero_norma='1333')
        Articulo.objects.create(norma=norma, rama=self.rama, numero_articulo='1', contenido='Texto anterior que debe conservarse')
        _, plan = self.revisar()
        resultado = self.cargar(plan)
        self.assertTrue(Articulo.objects.get(norma=norma, numero_articulo='1').estado)
        self.assertEqual(resultado.revision['normas_creadas'], [])
        self.assertEqual(resultado.revision['normas_reutilizadas'][0]['id'], norma.pk)

    def test_identidad_o_alternativa_pendiente_impide_publicar_todas(self):
        from rest_framework.exceptions import ValidationError
        _, plan = self.revisar(texto=TEXTO.replace('LEY N° 1333', 'LEY N° 1582\nMODIFICACIÓN DE LA LEY DE PENSIONES'))
        with self.assertRaises(ValidationError):
            validar_anexos(plan['anexos'], self.rama)
        self.assertFalse(Articulo.objects.filter(norma=self.principal).exists())

    def test_fallo_del_anexo_revierte_articulos_y_normas_creadas(self):
        _, plan = self.revisar()
        fuente = self.fuente(plan)
        from modulo_catalogo.services.revision_carga_service import aplicar_carga_revisada
        def aplicar(*args, **kwargs):
            if args[0].pk != self.principal.pk:
                raise ValueError('Fallo del anexo')
            return aplicar_carga_revisada(*args, **kwargs)
        with patch('modulo_catalogo.services.carga_pdf_service._obtener_modelo'), patch('modulo_ia.services.vectorizacion_service.vectorizar_textos', return_value=[[0.1] * 768]), patch('modulo_catalogo.services.carga_compilacion_service.aplicar_carga_revisada', side_effect=aplicar):
            with self.assertRaisesMessage(ValueError, 'Fallo del anexo'):
                aplicar_compilacion(self.principal, self.rama, plan, 'articulos', ['1'], fuente.pk)
        self.assertFalse(Articulo.objects.filter(norma=self.principal).exists())
        self.assertFalse(Norma.objects.filter(numero_norma='1333').exists())

    def test_alternativas_ambiguas_del_anexo_impiden_confirmar(self):
        from rest_framework.exceptions import ValidationError
        _, plan = self.revisar(texto=TEXTO + '\nARTÍCULO 104. Otra versión diferente del delito ambiental.')
        self.assertTrue(plan['anexos'][0]['ambiguedades_pendientes'])
        with self.assertRaises(ValidationError):
            validar_anexos(plan['anexos'], self.rama)

    def test_identidad_verificada_y_alternativa_se_aplican_al_anexo_correspondiente(self):
        import json
        texto = TEXTO.replace('LEY N° 1333', 'LEY N° 1582\nMODIFICACIÓN DE LA LEY DE PENSIONES')
        _, plan = self.revisar(texto=texto, identidades_secciones=json.dumps({'1': {'nombre': 'Ley de Pensiones', 'tipo_norma': 'Ley', 'numero_norma': '065', 'fecha_norma': '2010-12-10'}}))
        self.assertFalse(plan['anexos'][0]['identidad_por_verificar'])
        self.assertEqual(plan['anexos'][0]['metadatos']['numero_norma'], '065')

    def test_numero_con_cero_inicial_no_duplica_norma_conocida(self):
        Norma.objects.create(nombre='Ley Electoral', tipo_norma='Ley', numero_norma='26')
        _, plan = self.revisar(texto=TEXTO.replace('1333', '026'))
        self.assertEqual(Norma.objects.get(numero_norma='26').pk, plan['anexos'][0]['norma_id'])

    def test_fecha_y_titulo_fuente_se_conservan_al_identificar_norma_destinataria(self):
        import json
        texto = ('LEY N° 900\nLEY DE 10 DE ENERO DE 2020\nARTÍCULO 1. Texto principal.\n'
                 'Ley Nº 1582\nLEY DE 01 DE OCTUBRE DE 2024\nMODIFICACIÓN DE LA LEY DE PENSIONES\n'
                 'ARTÍCULO 119. Delito de pensiones.\nARTÍCULO 120. Otro delito de pensiones.')
        for motor in ['clasico', 'qwen']:
            with self.subTest(motor=motor):
                respuesta, plan = self.revisar(motor, texto=texto, identidades_secciones=json.dumps({
                    '1': {'nombre': 'Ley de Pensiones', 'tipo_norma': 'Ley', 'numero_norma': '065', 'fecha_norma': '2010-12-10'}
                }))
                anexo = respuesta['anexos'][0]
                self.assertEqual(anexo['documento_fuente']['nombre'], 'Ley de Pensiones')
                self.assertEqual(anexo['documento_fuente']['numero_norma'], '1582')
                self.assertEqual(anexo['documento_fuente']['fecha_norma'], '2024-10-01')
                self.assertEqual(anexo['metadatos']['fecha_norma'], '2010-12-10')
                self.assertEqual(plan['anexos'][0]['metadatos']['documento_fuente'], anexo['documento_fuente'])
        self.cargar(plan)
        documento = DocumentoNorma.objects.get(norma__numero_norma='065')
        self.assertEqual(documento.metadatos['documento_fuente']['fecha_norma'], '2024-10-01')
        self.assertEqual(documento.metadatos['documento_fuente']['nombre'], 'Ley de Pensiones')
