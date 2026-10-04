from datetime import date
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from modulo_catalogo.models import Norma, RamaDerecho, Articulo, DocumentoNorma, DisposicionNormativa, CambioNormativo
from modulo_catalogo.services.lectura_normativa_service import extraer_unidades, detectar_cambios, detectar_derogaciones_expresas
from modulo_catalogo.services.disposiciones_service import separar_unidades
from modulo_catalogo.services.revision_carga_service import aplicar_carga_revisada, filas_actuales, huella_catalogo
from modulo_usuarios.tests.factories import crear_usuario, crear_rol
from .test_validacion_pdf_endpoints import PDF_MINIMO_1_PAGINA

TEXTO = """ARTÍCULO 1. (OBJETO). Texto original de la nueva norma.
DISPOSICIONES TRANSITORIAS
PRIMERA. Un plazo transitorio que no se debe importar.
DISPOSICIÓN FINAL
ÚNICA. La aplicación de la presente Ley, no implicará recursos adicionales del Tesoro General de la Nación (TGN).
DISPOSICIÓN DEROGATORIA
ÚNICA. En el marco de la entrada en vigencia de la presente Ley, se derogan expresamente las siguientes disposiciones
del Código Penal:
1. El Parágrafo III del Artículo 323 Bis,
2. El Artículo 281 Quater. (Pornografía y espectáculos obscenos con niños, niñas o adolescentes).
Remítase al Órgano Ejecutivo para fines constitucionales.
Es dada en la Sala de Sesiones de la Asamblea Legislativa Plurinacional, a los tres días del mes de septiembre del año dos mil veinticinco.
Por tanto, la promulgo para que se tenga y cumpla como Ley del Estado Plurinacional de Bolivia.
"""


class DisposicionesTests(APITestCase):
    def setUp(self):
        cache.clear()
        usuario = crear_usuario('disposiciones.abogado', rol=crear_rol('Abogado'))
        self.client.force_authenticate(usuario)
        self.rama = RamaDerecho.objects.create(nombre='Penal disposiciones')
        self.norma = Norma.objects.create(nombre='Ley 1636', tipo_norma='Ley', numero_norma='1636', fecha_norma=date(2025, 9, 10))
        self.penal = Norma.objects.get(sigla='CP')
        self.penal.fecha_norma = date(1972, 1, 1)
        self.penal.save()
        Articulo.objects.create(norma=self.penal, rama=self.rama, numero_articulo='323 Bis', contenido='I. Texto intacto.\nIII. Parte derogada.')
        Articulo.objects.create(norma=self.penal, rama=self.rama, numero_articulo='281 Quater', contenido='Texto histórico.')
        self.documento = DocumentoNorma.objects.create(norma=self.norma, rama=self.rama, nombre_original='1636.pdf',
            ruta_archivo='1636.pdf', tamano=10, metadatos={'tipo_norma': 'Ley', 'numero_norma': '1636', 'fecha_norma': '2025-09-10'})

    def unidades(self):
        return extraer_unidades(TEXTO, 'clasico')

    def test_ejemplo_detecta_ambos_destinos_sin_depender_de_qwen(self):
        articulos, disposiciones = separar_unidades(self.unidades())
        self.assertEqual([u['numero'] for u in articulos], ['1'])
        self.assertEqual([u['numero'] for u in disposiciones], ['DF ÚNICA', 'DD ÚNICA'])
        self.assertNotIn('DISPOSICIÓN', articulos[0]['texto'])
        self.assertNotIn('Remítase', disposiciones[-1]['texto'])
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'cambios': []}) as consulta:
            cambios = detectar_cambios(disposiciones)
        consulta.assert_not_called()
        destinos = {c['unidad']: c['alcance'] for c in cambios}
        self.assertEqual(destinos, {'323 BIS': 'Parágrafo III', '281 QUATER': 'total'})
        self.assertTrue(all(c['unidad_fuente'] == 'DD ÚNICA' for c in cambios))

    def test_revision_clasica_devuelve_avisos_y_tabla_aparte(self):
        with patch('modulo_catalogo.views.revision_carga_view.extraer_texto_pdf_bytes', return_value=TEXTO):
            resp = self.client.post('/api/catalogo/cargar-articulos/revisar/', {
                'archivo': SimpleUploadedFile('1636.pdf', PDF_MINIMO_1_PAGINA, content_type='application/pdf'),
                'norma_id': self.norma.pk, 'rama_id': self.rama.pk, 'motor_lectura': 'clasico'}, format='multipart')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(len(resp.data['articulos']), 1)
        self.assertEqual(len(resp.data['disposiciones']), 2)
        self.assertEqual(len(resp.data['cambios_normativos']), 2)
        self.assertTrue(all(c['destino_catalogo']['encontrado'] for c in resp.data['cambios_normativos']), resp.data['cambios_normativos'])
        self.assertEqual(CambioNormativo.objects.count(), 0)

    def cargar_disposiciones(self):
        unidades = self.unidades()
        _, disposiciones = separar_unidades(unidades)
        self.documento.analisis_normativo = {'cambios': detectar_derogaciones_expresas(disposiciones)}
        self.documento.save()
        with patch('modulo_catalogo.services.carga_pdf_service._obtener_modelo') as modelo:
            resultado = aplicar_carga_revisada(self.norma, self.rama, unidades, 'articulos', [],
                huella_catalogo(filas_actuales(self.norma.pk, self.rama.pk)), self.documento.pk)
        modelo.assert_not_called()
        return resultado

    def test_disposiciones_guardadas_sin_articulos_seleccionados_conservan_avisos(self):
        resultado = self.cargar_disposiciones()
        self.assertEqual(resultado.revision['disposiciones'], 2)
        self.assertEqual(resultado.revision['normas_guardadas'], 1)
        self.assertEqual(DisposicionNormativa.objects.count(), 2)
        self.assertFalse(Articulo.objects.filter(norma=self.norma).exists())
        self.assertEqual(CambioNormativo.objects.count(), 2)
        self.assertTrue(all(c.estado_revision == 'pendiente' for c in CambioNormativo.objects.all()))
        self.assertEqual(len(resultado.resumen()['revision']['avisos']), 2)
        self.assertIn('disposición derogatoria única', resultado.revision['avisos'][0]['mensaje'])

    def test_endpoint_separado_muestra_disposiciones_y_avisos_de_la_fuente(self):
        self.cargar_disposiciones()
        resp = self.client.get('/api/catalogo/disposiciones/', {'norma_id': self.norma.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 2)
        derogatoria = next(d for d in resp.data['results'] if d['tipo'] == 'derogatoria')
        self.assertEqual(len(derogatoria['avisos']), 2)
        self.assertTrue(all(a['estado'] == 'pendiente' for a in derogatoria['avisos']))
        lista = self.client.get('/api/catalogo/articulos/', {'norma_id': self.norma.pk})
        self.assertEqual(lista.data['count'], 0)

    def test_abrogacion_en_final_tambien_se_detecta_sin_modelo(self):
        unidad = {'numero': 'DF TERCERA', 'tipo_unidad': 'final', 'texto':
            'TERCERA (Abrogatorias).- Queda abrogada la Ley de Ejecución de Penas aprobada mediante el Decreto Ley No 11080, con todas sus modificaciones.'}
        cambios = detectar_derogaciones_expresas([unidad])
        self.assertEqual(len(cambios), 1)
        self.assertEqual(cambios[0]['operacion'], 'abroga')
        self.assertEqual(cambios[0]['norma'], 'Decreto Ley 11080')

    def test_clausula_generica_y_final_financiera_no_derogan_articulos(self):
        unidades = [{'numero': 'DD ÚNICA', 'tipo_unidad': 'derogatoria', 'texto': 'Quedan derogadas todas las disposiciones contrarias a esta Ley.'},
                    {'numero': 'DF ÚNICA', 'tipo_unidad': 'final', 'texto': 'No implicará recursos adicionales del TGN.'}]
        self.assertEqual(detectar_derogaciones_expresas(unidades), [])


    def test_numeral_de_lista_en_misma_linea_no_se_toma_como_articulo_2(self):
        unidad = {'numero': 'DD ÚNICA', 'tipo_unidad': 'derogatoria', 'texto':
            'ÚNICA. Se derogan las siguientes disposiciones del Código Penal: 1. El Parágrafo III del Artículo 323 Bis, 2. El Artículo 281 Quater.'}
        cambios = detectar_derogaciones_expresas([unidad])
        self.assertEqual({c['unidad'] for c in cambios}, {'323 BIS', '281 QUATER'})


    def test_cabecera_con_ordinal_grado_no_impide_reconstruir_unidades(self):
        from modulo_catalogo.services.lectura_normativa_service import reconstruir, localizar_clasico
        from modulo_catalogo.services.carga_pdf_service import extraer_titulo_articulo
        lineas = ['ARTICULO 1º (Objeto).- Texto.', 'DISPOSICIÓN FINAL', 'ÚNICA. Texto final.']
        unidades = reconstruir(localizar_clasico(lineas), lineas, extraer_titulo_articulo)
        self.assertEqual([u['numero'] for u in unidades], ['1', 'DF ÚNICA'])
        self.assertIn('1º', unidades[0]['texto'])


    def test_recuperacion_retira_solo_detecciones_erroneas_pendientes_y_es_repetible(self):
        import io
        from django.core.management import call_command
        falso = CambioNormativo.objects.create(fuente=self.documento, operacion='deroga', unidad_fuente='DD ÚNICA',
            referencia={'norma': 'Código Penal', 'unidad': '2', 'alcance': 'total'}, cita='Texto que confundió un numeral de lista.', huella='error-numeral')
        with patch('modulo_catalogo.management.commands.recuperar_disposiciones.default_storage.open', side_effect=lambda *args: io.BytesIO(b'pdf')), patch(
            'modulo_catalogo.management.commands.recuperar_disposiciones.extraer_texto_pdf_bytes', return_value=TEXTO):
            call_command('recuperar_disposiciones', stdout=io.StringIO())
            call_command('recuperar_disposiciones', stdout=io.StringIO())
        falso.refresh_from_db()
        self.assertEqual(falso.estado_revision, 'descartado')
        self.assertEqual(CambioNormativo.objects.filter(estado_revision='pendiente').count(), 2)
        self.assertEqual(CambioNormativo.objects.filter(estado_revision='confirmado').count(), 0)
        self.assertEqual(DisposicionNormativa.objects.count(), 2)
