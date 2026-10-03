from unittest.mock import Mock, patch
from django.test import SimpleTestCase, override_settings
from django.core.cache import cache
from modulo_catalogo.services.lectura_normativa_service import (
    extraer_unidades, detectar_cambios, ajustar_cambio_literal, bloques_efectos, extraer_metadatos,
)
from modulo_catalogo.services.ollama_normativo import consultar

TEXTO = """ARTÍCULO 1. (OBJETO). Se regula la ejecución de penas.
DISPOSICIONES TRANSITORIAS
PRIMERA (Trabajo).- El estudio anterior se reconoce mediante resolución judicial.
TERCERA.- DEROGADO por Disposición de la Ley 2446 de fecha 19 de marzo del 2003
DISPOSICIONES FINALES
PRIMERA (Reglamentación).- Se reglamentará dentro de noventa días desde su publicación.
TERCERA (Abrogatorias).- Queda abrogada la Ley de Ejecución de Penas y Sistema Penitenciario, aprobada mediante el Decreto Ley No 11080, de fecha 19 de diciembre de 1973.
DISPOSICIÓN DEROGATORIA
ÚNICA. Quedan derogadas todas las disposiciones contrarias a esta Ley.
"""

def candidato(cita, **extra):
    return {'operacion': 'abroga', 'norma': '', 'unidad': '', 'alcance': 'total',
            'cita': cita, 'origen': 'clausula', 'causante': '', 'fecha_causante': '', **extra}

class LecturaNormativaTests(SimpleTestCase):
    def test_clasico_conserva_disposiciones_y_ordinales_repetidos_entre_secciones(self):
        unidades = extraer_unidades(TEXTO, 'clasico')
        self.assertEqual([u['numero'] for u in unidades], ['1', 'DT PRIMERA', 'DT TERCERA', 'DF PRIMERA', 'DF TERCERA', 'DD ÚNICA'])
        self.assertIn('Decreto Ley No 11080', unidades[-2]['texto'])
        self.assertNotIn('DISPOSICIONES', unidades[0]['texto'])

    @patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'unidades': []})
    def test_control_de_cobertura_conserva_texto_si_modelo_omite_cabeceras(self, consulta):
        avisos = []
        unidades = extraer_unidades(TEXTO, 'qwen', avisos)
        self.assertEqual(len(unidades), 6)
        self.assertEqual(unidades[2]['texto'], TEXTO.splitlines()[3])
        self.assertTrue(avisos)

    def test_articulos_dentro_de_cita_no_son_unidades_de_la_norma_modificatoria(self):
        texto = 'ARTÍCULO 1. Se modifica la Ley 260 con este texto:\n“ARTÍCULO 25. Texto citado.\nARTÍCULO 26. Otra parte de la cita.”\nARTÍCULO 2. Texto principal suficientemente largo.'
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'unidades': []}):
            unidades = extraer_unidades(texto, 'qwen')
        self.assertEqual([u['numero'] for u in unidades], ['1', '2'])
        self.assertIn('ARTÍCULO 26', unidades[0]['texto'])

    def test_nota_derogada_corrige_solo_con_evidencia_literal_y_fecha_explicita(self):
        u = {'numero': 'DT TERCERA', 'texto': TEXTO.splitlines()[3]}
        c = ajustar_cambio_literal(candidato(u['texto'], origen='nota_editorial', norma=u['texto']), u)
        self.assertEqual((c['operacion'], c['norma'], c['unidad']), ('deroga', '', 'DT TERCERA'))
        self.assertEqual((c['causante'], c['fecha_causante']), ('Ley 2446', '2003-03-19'))

    def test_general_no_identifica_articulos_por_inferencia(self):
        u = {'numero': 'DD ÚNICA', 'texto': TEXTO.splitlines()[8]}
        c = ajustar_cambio_literal(candidato(u['texto'], norma='Código Penal', unidad='25'), u)
        self.assertEqual((c['operacion'], c['norma'], c['unidad']), ('general', '', ''))

    def test_plazo_no_es_abrogacion_aunque_modelo_lo_diga(self):
        u = {'numero': 'DF PRIMERA', 'texto': TEXTO.splitlines()[5]}
        self.assertEqual(ajustar_cambio_literal(candidato(u['texto']), u)['operacion'], 'temporal')

    def test_abrogacion_identifica_decreto_ley_completo(self):
        u = {'numero': 'DF TERCERA', 'texto': TEXTO.splitlines()[6]}
        c = ajustar_cambio_literal(candidato(u['texto'], unidad='TERCERA'), u)
        self.assertEqual((c['norma'], c['unidad'], c['alcance']), ('Decreto Ley 11080', '', 'total'))

    def test_incorporacion_no_abroga_ley_o_articulo(self):
        u = {'numero': 'ÚNICO', 'texto': 'ARTÍCULO ÚNICO. Se incorpora el Parágrafo VI al Artículo 25 de la Ley N° 260.'}
        c = ajustar_cambio_literal(candidato(u['texto'], alcance='Parágrafo VI'), u)
        self.assertEqual((c['operacion'], c['norma'], c['unidad']), ('incorpora', 'Ley 260', '25'))

    @patch('modulo_catalogo.services.lectura_normativa_service.consultar')
    def test_rechaza_evidencia_inventada(self, consulta):
        consulta.return_value = {'cambios': [candidato('Queda abrogada una ley inexistente.') ]}
        with self.assertRaisesMessage(ValueError, 'evidencia'):
            detectar_cambios([{'numero': '1', 'texto': 'ARTÍCULO 1. Se modifica el Código Penal.'}])

    def test_fragmentos_no_truncan_la_disposicion_final(self):
        texto = ('Contenido largo sin una línea final. ' * 500) + ' Queda abrogada la Ley 100.'
        bloques = bloques_efectos(texto)
        self.assertTrue(all(len(b) <= 4200 for b in bloques))
        self.assertTrue(bloques[-1].endswith('Queda abrogada la Ley 100.'))

    @patch('modulo_catalogo.services.lectura_normativa_service.consultar')
    def test_numero_de_norma_que_no_existe_en_cabecera_se_rechaza(self, consulta):
        consulta.return_value = {'tipo_norma': 'Ley', 'numero_norma': '999', 'fecha_norma': ''}
        with self.assertRaisesMessage(ValueError, 'identidad'):
            extraer_metadatos('LEY N° 260. Texto principal.')

    @override_settings(OLLAMA_NORMATIVO_MODELO='qwen3.5:2b', OLLAMA_NORMATIVO_URL='http://127.0.0.1:11434',
        OLLAMA_NORMATIVO_CONTEXTO=4096, OLLAMA_NORMATIVO_TIMEOUT=180, OLLAMA_NORMATIVO_KEEP_ALIVE='0')
    @patch('modulo_catalogo.services.ollama_normativo.requests.post')
    def test_respuesta_incompleta_no_se_publica(self, post):
        cache.clear()
        post.return_value.json.return_value = {'done': True, 'done_reason': 'length', 'message': {'content': '{}'}}
        with self.assertRaisesMessage(ValueError, 'incompleta'):
            consultar('Prueba', 'texto', {'type': 'object'})



class AlcanceNormativoTests(SimpleTestCase):
    def test_localiza_paragrafo_ii_sin_derogar_paragrafo_i_o_iii(self):
        from types import SimpleNamespace
        from modulo_catalogo.services.alcance_normativo_service import identificar_parte
        articulo = SimpleNamespace(contenido='ARTÍCULO 25. Título\nI. Parte vigente.\nII. Parte afectada.\nIII. Otra parte vigente.')
        parte = identificar_parte('Se deroga el Parágrafo II del Artículo 25.', 'total', articulo)
        self.assertEqual(parte['tipo'], 'parcial')
        self.assertEqual(parte['partes'][0]['fragmento'], 'II. Parte afectada.')
        self.assertTrue(parte['localizado'])

    def test_localiza_inciso_dentro_de_paragrafo_sin_confundir_otros_incisos(self):
        from types import SimpleNamespace
        from modulo_catalogo.services.alcance_normativo_service import identificar_parte
        texto = 'ARTÍCULO 25.\nI. Antes\na) Texto uno.\nb) Texto dos.\nII. Segundo\na) Conservado.\nb) Derogado.\nc) Conservado también.\nIII. Fin.'
        parte = identificar_parte('Se deroga el inciso b) del Parágrafo II del Artículo 25.', 'inciso b)', SimpleNamespace(contenido=texto))
        self.assertEqual(parte['partes'][0]['fragmento'], 'b) Derogado.')

    def test_ultimo_parrafo_sin_limites_claros_no_se_adivina(self):
        from types import SimpleNamespace
        from modulo_catalogo.services.alcance_normativo_service import identificar_parte
        parte = identificar_parte('Queda derogado el último párrafo del Artículo 47.', 'último párrafo', SimpleNamespace(contenido='ARTÍCULO 47.\nPrimera línea.\nSegunda línea.'))
        self.assertEqual(parte['tipo'], 'parcial')
        self.assertFalse(parte['localizado'])

    def test_frase_citada_localiza_solo_texto_literamente_afectado(self):
        from types import SimpleNamespace
        from modulo_catalogo.services.alcance_normativo_service import identificar_parte
        parte = identificar_parte('Se deroga la frase “trabajo obligatorio” del Artículo 5.', 'frase', SimpleNamespace(contenido='ARTÍCULO 5. Se establece trabajo obligatorio y estudio voluntario.'))
        self.assertEqual(parte['partes'][0]['fragmento'], 'trabajo obligatorio')

    def test_paragrafos_ii_y_iii_generan_dos_fragmentos(self):
        from types import SimpleNamespace
        from modulo_catalogo.services.alcance_normativo_service import identificar_parte
        parte = identificar_parte('Se derogan los Parágrafos II y III del Artículo 25.', 'parcial', SimpleNamespace(contenido='I. Vigente\nII. Uno\nIII. Dos\nIV. Vigente'))
        self.assertEqual([p['fragmento'] for p in parte['partes']], ['II. Uno', 'III. Dos'])



class DisposicionesConNumeralesTests(SimpleTestCase):
    def test_lista_de_requisitos_no_se_convierte_en_tres_disposiciones(self):
        texto = 'ARTÍCULO 1. Objeto de la Ley y normas suficientemente largas.\nDISPOSICIONES TRANSITORIAS\nPRIMERA (Estudio).- Debe cumplir estos requisitos:\n1. Declaración jurada.\n2. Pruebas que respalden lo declarado.\n3. Certificado de la Junta.\nSEGUNDA (Régimen).- Las sanciones podrán revisarse por el Juez.\nTERCERA.- DEROGADO por Ley 2446 de 19 de marzo del 2003.'
        propuestas = {'unidades': [{'linea': 3, 'tipo': 'transitoria', 'numero': '1'}, {'linea': 4, 'tipo': 'transitoria', 'numero': '2'}, {'linea': 5, 'tipo': 'transitoria', 'numero': '3'}]}
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value=propuestas):
            unidades = extraer_unidades(texto, 'qwen')
        self.assertEqual([u['numero'] for u in unidades], ['1', 'DT PRIMERA', 'DT SEGUNDA', 'DT TERCERA'])
        self.assertIn('3. Certificado', unidades[1]['texto'])

    def test_disposicion_inline_no_pierde_su_contenido(self):
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'unidades': []}):
            unidades = extraer_unidades('DISPOSICIÓN DEROGATORIA ÚNICA. Quedan derogadas las disposiciones contrarias.', 'qwen')
        self.assertEqual(unidades[0]['numero'], 'DD ÚNICA')
        self.assertIn('Quedan derogadas', unidades[0]['texto'])

    def test_texto_sustitutivo_citado_no_agrega_destinos_de_otra_norma(self):
        from modulo_catalogo.services.lectura_normativa_service import texto_operativo
        texto = 'ARTÍCULO ÚNICO. Se incorpora el Parágrafo VI al Artículo 25 de la Ley 260, con el siguiente texto:\n“VI. Requisitos del Parágrafo II del Artículo 227 de la Constitución.”'
        fuente = texto_operativo(texto)
        self.assertIn('Artículo 25', fuente)
        self.assertNotIn('Artículo 227', fuente)



class MetadatosYAlcanceLiteralTests(SimpleTestCase):
    @patch('modulo_catalogo.services.lectura_normativa_service.consultar')
    def test_numero_legal_no_guarda_el_prefijo_n(self, consulta):
        consulta.return_value = {'tipo_norma': 'Ley', 'numero_norma': 'N° 1773', 'fecha_norma': '2026-10-02'}
        self.assertEqual(extraer_metadatos('LEY N° 1773 DE 2 DE OCTUBRE DE 2026')['numero_norma'], '1773')

    def test_alcance_del_paragrafo_no_depende_de_un_resumen_erroneo_del_modelo(self):
        u = {'numero': 'ÚNICO', 'texto': 'ARTÍCULO ÚNICO. Se incorpora el Parágrafo VI al Artículo 25 de la Ley N° 260.'}
        c = ajustar_cambio_literal(candidato(u['texto'], alcance='No afecta a ningún artículo.'), u)
        self.assertEqual((c['unidad'], c['alcance']), ('25', 'Parágrafo VI'))


class DestinosConAlcanceDistintoTests(SimpleTestCase):
    def test_ley_2446_separa_articulo_46_parrafo_47_y_transitoria(self):
        from types import SimpleNamespace
        from modulo_catalogo.services.alcance_normativo_service import identificar_parte
        cita = 'Quedan derogados el Artículo 46, el último párrafo del Artículo 47, y la Disposición Transitoria TERCERA de la Ley 2298.'
        contenido = 'Título y primer párrafo.\n\nÚltimo párrafo afectado.'
        for numero, tipo in [('46', 'total'), ('47', 'parcial'), ('DT TERCERA', 'total')]:
            with self.subTest(numero=numero):
                parte = identificar_parte(cita, 'Último párrafo', SimpleNamespace(numero_articulo=numero, contenido=contenido))
                self.assertEqual(parte['tipo'], tipo)
                if numero == '47':
                    self.assertEqual(parte['partes'][0]['fragmento'], 'Último párrafo afectado.')
                    self.assertTrue(parte['localizado'])

    def test_alcance_compartido_ambiguo_exige_revision_literal(self):
        from types import SimpleNamespace
        from modulo_catalogo.services.alcance_normativo_service import identificar_parte
        parte = identificar_parte('Se deroga el Parágrafo II del Artículo 25 y del Artículo 26.', 'parcial', SimpleNamespace(numero_articulo='25', contenido='I. Antes\nII. Afectado\nIII. Después'))
        self.assertEqual(parte['tipo'], 'parcial')
        self.assertFalse(parte['localizado'])
