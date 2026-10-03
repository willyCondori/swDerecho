"""Regresiones basadas en los PDF facilitados para revisar el extractor."""
from pathlib import Path

from django.test import SimpleTestCase

from modulo_catalogo.services.carga_pdf_service import (
    DocumentoConVariasNormasError,
    construir_texto_embedding,
    dividir_documento_por_normas,
    dividir_por_articulos,
    extraer_titulo_articulo,
)

FIXTURES = Path(__file__).parent / 'fixtures'


class ExtractorNormasRealesTests(SimpleTestCase):
    def fixture(self, nombre):
        return (FIXTURES / nombre).read_text(encoding='utf-8')

    def test_ley_1173_conserva_citas_dentro_del_articulo_modificatorio(self):
        articulos = dividir_por_articulos(self.fixture('ley_1173_inicio.txt'))
        self.assertEqual([a['numero'] for a in articulos], ['1', '2', '3', '4'])
        por_numero = {a['numero']: a['texto'] for a in articulos}
        for numero in [23, 24, 30]:
            self.assertIn(f'Artículo {numero}', por_numero['2'])
        for numero in [52, 53, 54, 56, 109]:
            self.assertIn(f'Artículo {numero}', por_numero['3'])
        self.assertIn('ajenas a su naturaleza', por_numero['3'])
        self.assertGreater(len(por_numero['3']), 9000)

    def test_ley_348_conserva_articulos_penales_citados(self):
        articulos = dividir_por_articulos(self.fixture('ley_348_reformas.txt'))
        self.assertEqual([a['numero'] for a in articulos], ['83', '84'])
        self.assertTrue(any('Artículo 252' in a['texto'] for a in articulos))

    def test_cpp_cabeceras_unidas_sin_punto_entre_articulos(self):
        articulos = dividir_por_articulos(self.fixture('cpp_179_181.txt'))
        self.assertEqual([a['numero'] for a in articulos], ['179', '180', '181'])
        self.assertIn('ALLANAMIENTO', articulos[1]['titulo'].upper())
        self.assertNotIn('Artículo 180', articulos[0]['texto'])

    def test_espacios_unicode_y_guion_discrecional(self):
        texto = ('Artículo\u00a01º.\u00ad\u00a0(OBJETO). Texto completo del primer artículo.\n'
                 'Artículo\u202f2º.\u00ad\u00a0(ALCANCE). Texto completo del segundo artículo.')
        articulos = dividir_por_articulos(texto)
        self.assertEqual([a['numero'] for a in articulos], ['1', '2'])
        self.assertEqual(articulos[0]['titulo'], 'Art. 1 - OBJETO')

    def test_titulo_no_usa_parentesis_de_una_cita_en_el_cuerpo(self):
        texto = 'ARTÍCULO 2. Se modifica el Código Penal (Ley 1970), en los términos siguientes.'
        self.assertEqual(extraer_titulo_articulo('2', texto), 'Art. 2')

    def test_embedding_retira_prefijo_completo_con_sufijo(self):
        texto = 'Art. 13 bis°.- (AUTORÍA). Son autores quienes realizan el hecho.'
        self.assertEqual(construir_texto_embedding('Art. 13 bis - AUTORÍA', texto),
                         'Art. 13 bis - AUTORÍA\nSon autores quienes realizan el hecho.')

    def test_compilacion_no_fusiona_numeros_de_dos_codigos(self):
        texto = ('CÓDIGO PENAL\nArtículo 1. (OBJETO). Texto del primer código.\n'
                 'Artículo 2. (ALCANCE). Texto de alcance del primer código.\n'
                 'Artículo 364. (FINAL). Texto final del primer código.\n'
                 'CÓDIGO DE PROCEDIMIENTO PENAL\n'
                 'Artículo 1. (OBJETO). Texto del segundo código.\n'
                 'Artículo 2. (ALCANCE). Texto de alcance del segundo código.')
        secciones = dividir_documento_por_normas(texto)
        self.assertEqual(len(secciones), 2)
        self.assertIn('primer código', secciones[0]['articulos'][0]['texto'])
        self.assertIn('segundo código', secciones[1]['articulos'][0]['texto'])
        with self.assertRaisesRegex(DocumentoConVariasNormasError, 'varias normas'):
            dividir_por_articulos(texto)
        self.assertEqual(dividir_por_articulos(texto, seccion_documento=1), secciones[1]['articulos'])

    def test_transitorios_con_numeracion_reiniciada_no_reemplazan_articulos(self):
        texto = ('ARTÍCULO 1. El texto principal del primer artículo.\n'
                 'ARTÍCULO 2. El texto principal del segundo artículo.\n'
                 'ARTÍCULO 149. El texto principal del último artículo.\n'
                 'ARTICULOS TRANSITORIOS\nARTÍCULO 1. Un texto transitorio distinto.\n'
                 'ARTÍCULO 2. Otro texto transitorio distinto.')
        articulos = dividir_por_articulos(texto)
        self.assertEqual([a['numero'] for a in articulos], ['1', '2', '149'])
        self.assertNotIn('transitorio', articulos[-1]['texto'])

    def test_disposicion_final_con_numero_consecutivo_se_conserva(self):
        texto = ('Art. 363 ter.- (DELITO). El texto completo de este delito.\n'
                 'DISPOSICIONES TRANSITORIAS\nArt. 364.- (ABROGACIÓN). Se abroga la ley anterior.\n'
                 'FUENTE\nInformación editorial del documento.')
        articulos = dividir_por_articulos(texto)
        self.assertEqual([a['numero'] for a in articulos], ['363 ter', '364'])
        self.assertNotIn('Información editorial', articulos[-1]['texto'])
