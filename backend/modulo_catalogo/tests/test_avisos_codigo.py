from unittest.mock import patch
from django.test import SimpleTestCase
from modulo_catalogo.services.algoritmos_normativos_service import detectar_cambios_literales
from modulo_catalogo.services.lectura_normativa_service import detectar_cambios
from modulo_catalogo.services.revision_carga_service import indica_derogacion


class AvisosCodigoTests(SimpleTestCase):
    def ambos(self, unidad):
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', side_effect=AssertionError('La evidencia literal no requiere Qwen')):
            resultados = [detectar_cambios_literales([unidad]), detectar_cambios([unidad])]
        self.assertEqual(resultados[0], resultados[1])
        return resultados[0]

    def test_palabras_de_delitos_y_penas_no_son_reglas_temporales(self):
        for texto in ['Artículo 4. Nadie será condenado sin ley penal vigente. Durante su vigencia se aplicará.',
                      'Artículo 26 Ter. Conforme normativa vigente, observando disposiciones legales en vigencia.',
                      'Artículo 345 Bis. No depositare los aportes dentro de los plazos establecidos para el pago.',
                      'Artículo 324. El que fabricare una publicación obscena será sancionado.']:
            with self.subTest(texto=texto):
                self.assertEqual(self.ambos({'numero': '4', 'texto': texto}), [])

    def test_entrada_en_vigor_y_reglamentacion_si_generan_aviso(self):
        for unidad in [
            {'numero': '365', 'texto': 'Artículo 365. (Vigencia) Este código regirá a partir del día dos de abril de 1973.'},
            {'numero': 'DF PRIMERA', 'tipo_unidad': 'final', 'texto': 'PRIMERA. Se reglamentará en un plazo de noventa días desde la publicación.'}]:
            self.assertEqual(self.ambos(unidad)[0]['operacion'], 'temporal')

    def test_nota_articulo_76_identifica_no_punto_y_cuenta_derogacion(self):
        unidad = {'numero': '76', 'texto': 'Artículo 76. (Delincuente Campesino)\nDerogado por Disposición Final Cuarta de la Ley No. 2298 de 20 de diciembre de 2001.'}
        cambio = self.ambos(unidad)[0]
        self.assertEqual((cambio['causante'], cambio['fecha_causante']), ('Ley 2298', '2001-12-20'))
        self.assertTrue(indica_derogacion(unidad))

    def test_nota_colectiva_distribuye_derogacion_a_todo_el_rango(self):
        for numero, lista, esperados in [('65', '59 al 65', range(59, 66)), ('69', '66 al 69', range(66, 70))]:
            unidad = {'numero': numero, 'texto': f'Artículo {numero}. (Efectos).\nLos Arts. {lista} fueron Derogados por la Disposición Final, Sexta de la Ley 1970 de 25\nde mrzo de 1999, Código Procedimiento Penal.'}
            cambios = self.ambos(unidad)
            self.assertEqual([c['unidad'] for c in cambios], [str(n) for n in esperados])
            self.assertTrue(all(c['operacion'] == 'deroga' and c['alcance'] == 'total' and c['causante'] == 'Ley 1970' and c['fecha_causante'] == '1999-03-25' for c in cambios))
            self.assertTrue(all('mrzo' in c['cita'] and c['unidad_fuente'] == numero for c in cambios))
            self.assertTrue(indica_derogacion(unidad))

    def test_nota_colectiva_no_deroga_el_articulo_que_solo_la_cita(self):
        unidad = {'numero': '70', 'texto': 'Artículo 70. Texto vigente.\nLos Arts. 66 al 69 fueron Derogados por la Ley 1970 de 25 de marzo de 1999.'}
        self.assertFalse(indica_derogacion(unidad))
        self.assertEqual([c['unidad'] for c in self.ambos(unidad)], ['66', '67', '68', '69'])

    def test_referencia_narrativa_no_es_nota_colectiva(self):
        from modulo_catalogo.services.notas_normativas_service import notas_editoriales_colectivas
        unidad = {'numero': '1', 'texto': 'Artículo 1. Este relato recuerda que los Arts. 59 al 65 fueron derogados por Ley 1970.'}
        self.assertEqual(notas_editoriales_colectivas(unidad), [])

    def test_lista_colectiva_no_pierde_modificacion_del_articulo_anfitrion(self):
        unidad = {'numero': '313', 'texto': 'Artículo 313. (Rapto). Texto vigente.\nModificado por el Artículo 83 de la Ley 348 de 9 de marzo de 2013.\nNOTA.- Los Arts. 314, 315, 316 y 317 fueron Derogados por la Disposición Abrogatoria y Derogatoria Primera de Ley 348 de 9 de marzo de 2013.'}
        cambios = self.ambos(unidad)
        self.assertEqual([(c['unidad'], c['operacion']) for c in cambios], [('314', 'deroga'), ('315', 'deroga'), ('316', 'deroga'), ('317', 'deroga'), ('313', 'modifica')])
        self.assertFalse(indica_derogacion(unidad))

    def test_fecha_con_error_tipografico_dde_sin_alterar_evidencia(self):
        unidad = {'numero': '100', 'texto': 'Artículo 100. (Extinción)\nDerogado por Ley 1970 de 25 de marzo dde 1999.'}
        cambio = self.ambos(unidad)[0]
        self.assertEqual(cambio['fecha_causante'], '1999-03-25')
        self.assertIn('dde', cambio['cita'])

    def test_nota_modificacion_no_se_atribuye_al_decreto_original(self):
        unidad = {'numero': '177', 'texto': 'Artículo 177. Se sanciona el retardo en los plazos legales.\nModificado por disposición del Art. 2 de la Ley 1390 de 27 de agosto de 2021.'}
        cambio = self.ambos(unidad)[0]
        self.assertEqual((cambio['operacion'], cambio['origen'], cambio['causante'], cambio['unidad']),
                         ('modifica', 'nota_editorial', 'Ley 1390', '177'))

    def test_nota_del_capitulo_siguiente_no_incorpora_articulo_anterior(self):
        unidad = {'numero': '363 Ter', 'texto': 'Artículo 363 Ter. Delito informático.\nSe incorpora por Ley Nº 393 de 21 de agosto de 2013 el siguiente texto:\nCAPÍTULO XII\nDELITOS FINANCIEROS'}
        cambio = self.ambos(unidad)[0]
        self.assertEqual((cambio['operacion'], cambio['unidad'], cambio['causante']), ('general', '', 'Ley 393'))
        self.assertIn('capítulo siguiente', cambio['alcance'])

    def test_referencia_judicial_no_se_convierte_en_derogacion_o_plazo(self):
        unidad = {'numero': '324', 'texto': 'Artículo 324. Publicación de escritos.\nPárrafo declarado inconstitucional por Sentencia Constitucional SC 0034/2006; aclarado por Auto Constitucional AC 0039/2006-ECA.'}
        cambio = self.ambos(unidad)[0]
        self.assertEqual(cambio['operacion'], 'general')
        self.assertIn('Referencia judicial', cambio['alcance'])

    def test_referencia_en_cuerpo_no_declara_derogado_articulo_propio(self):
        unidad = {'numero': '1', 'texto': 'Artículo 1. Este procedimiento cita el Artículo 25, derogado por Ley 100. Otra regla.'}
        self.assertFalse(indica_derogacion(unidad))


    def test_fechas_con_erratas_de_segip_conservan_cita_y_no_completan_anios(self):
        ejemplos = [('25 marzo de 1999', '1999-03-25'), ('04 de juliio de 2022', '2022-07-04'), ('27 de agosto de 2021Ley', '2021-08-27'), ('27 de agosto de 202', '')]
        for literal, esperada in ejemplos:
            unidad = {'numero': '105', 'texto': f'Artículo 105. Texto del delito.\nModificado por Ley 1443 de {literal}.'}
            dato = self.ambos(unidad)[0]
            self.assertEqual(dato['fecha_causante'], esperada)
            self.assertIn(literal, dato['cita'])



class SufijosParenteticosTests(SimpleTestCase):
    def test_129_y_129_bis_son_distintos_sin_capitulo_en_cuerpo(self):
        from modulo_catalogo.services.lectura_normativa_service import extraer_unidades
        from modulo_catalogo.services.compilaciones_service import resolver_alternativas
        texto = ('Artículo 129. (Ultraje a los símbolos nacionales). Texto original.\n'
                 'Artículo 129 (Bis). Separatismo. Texto del delito.\n'
                 'Incorporado por disposición de la Ley No. 170 de 9 de septiembre de 2011.\n'
                 'CAPÍTULO III\nDELITOS CONTRA LA TRANQUILIDAD PÚBLICA\n'
                 'Artículo 130. (Instigación). Otro texto.')
        for motor in ['clasico', 'qwen']:
            with self.subTest(motor=motor), patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'unidades': []}):
                unidades = extraer_unidades(texto, motor)
                unidades, ambiguas = resolver_alternativas(unidades)
                self.assertEqual([u['numero'].casefold() for u in unidades], ['129', '129 bis', '130'])
                self.assertEqual(ambiguas, [])
                self.assertNotIn('CAPÍTULO III', unidades[1]['texto'])
                self.assertNotIn('DELITOS CONTRA LA TRANQUILIDAD PÚBLICA', unidades[1]['texto'])
                self.assertIn('Ley No. 170', unidades[1]['texto'])

    def test_parentesis_de_titulo_no_es_sufijo(self):
        from modulo_catalogo.services.lectura_normativa_service import extraer_unidades
        unidades = extraer_unidades('Artículo 129. (Ultraje). Texto suficiente del artículo.', 'clasico')
        self.assertEqual(unidades[0]['numero'], '129')

    def test_derogacion_con_bis_parentetico_no_afecta_articulo_base(self):
        from modulo_catalogo.services.lectura_normativa_service import detectar_cambios
        unidad = {'numero': 'DD ÚNICA', 'tipo_unidad': 'derogatoria',
                  'texto': 'ÚNICA. Se deroga el Artículo 129 (Bis) del Código Penal.'}
        for detector in [detectar_cambios, detectar_cambios_literales]:
            self.assertEqual([c['unidad'] for c in detector([unidad])], ['129 BIS'])

    def test_cabecera_quater_acentuado_se_reconstruye(self):
        from modulo_catalogo.services.lectura_normativa_service import extraer_unidades
        for motor in ['clasico', 'qwen']:
            with patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'unidades': []}):
                u = extraer_unidades('Artículo 177. Quáter (Alteración). Texto del primer delito.\nArtículo 181. Bis. Texto de otro delito.', motor)
                self.assertEqual([x['numero'].casefold() for x in u], ['177 quater', '181 bis'])

    def test_177_y_177_ter_derogado_no_son_versiones_del_mismo_articulo(self):
        from modulo_catalogo.services.lectura_normativa_service import extraer_unidades
        from modulo_catalogo.services.compilaciones_service import resolver_alternativas
        texto = ('Artículo 177. (Defraudación Tributaria). El que dolosamente no pague la deuda tributaria será sancionado.\n'
                 'Artículo 177. Ter Derogado (Emisión De Facturas, Notas Fiscales Y Documentos Equivalentes Sin Hecho Generador). '
                 'El que comercialice facturas sin hecho generador será sancionado.\n'
                 'Declarado Inconstitucional por Sentencia Constitucional SC 0100/2014, de 10 de enero.\n'
                 'Artículo 178. (Defraudación Aduanera). Texto de la siguiente unidad.')
        for motor in ['clasico', 'qwen']:
            with self.subTest(motor=motor), patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'unidades': []}):
                unidades, ambiguas = resolver_alternativas(extraer_unidades(texto, motor))
                self.assertEqual([u['numero'].casefold() for u in unidades], ['177', '177 ter', '178'])
                self.assertEqual(ambiguas, [])
                self.assertNotIn('Emisión De Facturas', unidades[0]['texto'])
                self.assertIn('SC 0100/2014', unidades[1]['texto'])

    def test_sufijos_antes_de_estado_editorial_se_conservan(self):
        from modulo_catalogo.services.lectura_normativa_service import ARTICULO, numero_literal
        for sufijo in ['Bis', 'Ter', 'Quáter', 'Quinquies']:
            with self.subTest(sufijo=sufijo):
                cabecera = ARTICULO.match(f'Artículo 177. {sufijo} Derogado (Título). Texto.')
                self.assertEqual(numero_literal(cabecera.group(1)).casefold(), f'177 {sufijo}'.casefold().replace('quáter', 'quater'))
