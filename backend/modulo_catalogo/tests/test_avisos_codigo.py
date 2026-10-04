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
