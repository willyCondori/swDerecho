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
        with self.assertRaisesMessage(ValueError, 'límite de respuesta'):
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


class RespuestasLargasTests(SimpleTestCase):
    def test_citas_se_adjuntan_sin_repetirlas_en_salida_del_modelo(self):
        texto = 'ÚNICA. Se derogan el Parágrafo III del Artículo 323 Bis, y el Artículo 281 Quater del Código Penal.'
        datos = [candidato('', operacion='deroga', norma='Código Penal', unidad=unidad, alcance=alcance)
                 for unidad, alcance in [('323 Bis', 'Parágrafo III'), ('281 Quater', 'total')]]
        for dato in datos: del dato['cita']
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'cambios': datos}) as consulta:
            resultados = detectar_cambios([{'numero': 'DD ÚNICA', 'texto': texto}])
        esquema = consulta.call_args.args[2]['properties']['cambios']['items']
        self.assertNotIn('cita', esquema['properties'])
        self.assertNotIn('cita', esquema['required'])
        self.assertEqual([c['cita'] for c in resultados], [texto, texto])

    def test_truncamiento_divide_bloque_y_conserva_indices_globales(self):
        from modulo_catalogo.services.lectura_normativa_service import consultar_fragmentado, ESTRUCTURA
        from modulo_catalogo.services.ollama_normativo import RespuestaIncompleta
        texto = '123: ARTÍCULO 5. ' + 'texto ' * 90 + '\n124: ARTÍCULO 6. ' + 'otro ' * 100
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', side_effect=[RespuestaIncompleta(), {'unidades': [{'linea': 123}]}, {'unidades': [{'linea': 124}]}]) as consulta:
            datos = consultar_fragmentado('Estructura', texto, ESTRUCTURA, 'unidades')
        self.assertEqual(datos, [{'linea': 123}, {'linea': 124}])
        self.assertTrue(consulta.call_args_list[1].args[1].startswith('123:'))
        self.assertTrue(consulta.call_args_list[2].args[1].startswith('124:'))

    def test_error_de_conexion_no_se_reintenta_como_truncamiento(self):
        from modulo_catalogo.services.lectura_normativa_service import consultar_fragmentado, ESTRUCTURA
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', side_effect=ValueError('Sin conexión')) as consulta:
            with self.assertRaisesMessage(ValueError, 'Sin conexión'):
                consultar_fragmentado('Estructura', 'Texto ' * 200, ESTRUCTURA, 'unidades')
        self.assertEqual(consulta.call_count, 1)

    def test_reintentos_agotados_no_publican_respuesta_parcial(self):
        from modulo_catalogo.services.lectura_normativa_service import consultar_fragmentado, ESTRUCTURA
        from modulo_catalogo.services.ollama_normativo import RespuestaIncompleta
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', side_effect=RespuestaIncompleta()):
            with self.assertRaisesMessage(RespuestaIncompleta, 'no se guardó'):
                consultar_fragmentado('Estructura', 'Texto. ' * 1200, ESTRUCTURA, 'unidades')


class DerogatoriaLey1636Tests(SimpleTestCase):
    def test_lista_numerada_separa_paragrafo_323_bis_y_articulo_281_quater(self):
        from types import SimpleNamespace
        from modulo_catalogo.services.alcance_normativo_service import identificar_parte
        texto = 'ÚNICA. Se derogan expresamente las siguientes disposiciones del Código Penal:\n1. El Parágrafo III del Artículo 323 Bis,\n2. El Artículo 281 Quater. (Pornografía y espectáculos obscenos).'
        for numero, tipo in [('323 Bis', 'parcial'), ('281 Quater', 'total')]:
            with self.subTest(numero=numero):
                parte = identificar_parte(texto, 'Parágrafo III', SimpleNamespace(numero_articulo=numero, contenido='I. Conservado\nII. Conservado\nIII. Afectado'))
                self.assertEqual(parte['tipo'], tipo)
                if tipo == 'parcial':
                    self.assertEqual(parte['partes'][0]['fragmento'], 'III. Afectado')
                    self.assertTrue(parte['localizado'])

    def test_sufijo_quater_no_se_pierde_en_destino_literal(self):
        texto = 'ÚNICA. Se deroga el Artículo 281 Quater del Código Penal.'
        cambio = ajustar_cambio_literal(candidato(texto, operacion='deroga', unidad='281'), {'numero': 'DD ÚNICA', 'texto': texto})
        self.assertEqual(cambio['unidad'], '281 Quater')


class ComillasInconsistentesTests(SimpleTestCase):
    def test_comilla_omitida_no_oculta_siguiente_articulo_principal(self):
        texto = 'ARTÍCULO 5. Se incorporan los Artículos 312 Quinquies, 312 Sexies y Artículo 323 Quater de la Ley 1768, con el siguiente texto:\n“ ARTÍCULO 312 Quinquies. Uno\nARTÍCULO 312 Sexies. Dos\nARTÍCULO 323 Quater. Tres\nARTÍCULO 6. Se modifica el Artículo 323 Bis de la Ley 1768, con el siguiente texto:\n“ ARTÍCULO 323 Bis. Nuevo texto.”\nARTÍCULO 7. Otro objeto.'
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'unidades': []}):
            unidades = extraer_unidades(texto, 'qwen')
        self.assertEqual([u['numero'] for u in unidades], ['5', '6', '7'])
        self.assertIn('ARTÍCULO 323 Quater', unidades[0]['texto'])

    def test_articulo_citado_sin_comilla_de_apertura_no_se_convierte_en_principal(self):
        texto = 'ARTÍCULO 9. Se modifican los Artículos 168, 169 y 170 de la Ley 548, con el siguiente texto:\n“ARTÍCULO 168. Uno\nARTÍCULO 169. Dos.”\nARTÍCULO 170. Tres.”\nARTÍCULO 10. Continúa la Ley.'
        datos = {'unidades': [{'linea': 3, 'tipo': 'articulo', 'numero': '170'}]}
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value=datos):
            unidades = extraer_unidades(texto, 'qwen')
        self.assertEqual([u['numero'] for u in unidades], ['9', '10'])

    def test_definicion_numerada_no_es_transitoria_sin_encabezado(self):
        texto = 'ARTÍCULO 4. Definiciones.\n6. Acoso sexual: definición extensa.\nARTÍCULO 5. Objeto posterior.'
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'unidades': [{'linea': 1, 'tipo': 'transitoria', 'numero': '6'}]}):
            unidades = extraer_unidades(texto, 'qwen')
        self.assertEqual([u['numero'] for u in unidades], ['4', '5'])

    def test_incorporacion_plural_excluye_cuerpo_sustitutivo(self):
        from modulo_catalogo.services.lectura_normativa_service import texto_operativo
        prefijo = 'ARTÍCULO 5. Se incorporan los Artículos 312 Sexies y 323 Ter de la Ley 1768, con el siguiente texto:'
        self.assertEqual(texto_operativo(prefijo + '\n“ARTÍCULO 312 Sexies. Se sanciona...\nARTÍCULO 323 Ter. Otro delito.”'), prefijo)


class MencionesSinEfectoTests(SimpleTestCase):
    def test_publicaciones_en_redes_y_titulo_de_capitulo_no_generan_reformas(self):
        texto = 'ARTÍCULO 4. Acoso sexual: mensajes y publicaciones en redes sociales.\nCAPÍTULO II\nINCORPORACIONES Y MODIFICACIONES AL CÓDIGO PENAL'
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar') as consulta:
            self.assertEqual(detectar_cambios([{'numero': '4', 'texto': texto}]), [])
        consulta.assert_not_called()


class DestinosLiterales1636Tests(SimpleTestCase):
    def test_derogatoria_corrige_prefijos_norma_y_nota_editorial_inventada(self):
        texto = 'ÚNICA. En el marco de la entrada en vigencia de la presente Ley, se derogan expresamente las siguientes disposiciones del Código Penal:\n1. El Parágrafo III del Artículo 323 Bis,\n2. El Artículo 281 Quater.'
        dato = candidato('', operacion='deroga', norma='El Parágrafo III del Artículo 323 Bis', unidad='ARTÍCULO 323 BIS', origen='nota_editorial', causante='Ley X')
        del dato['cita']
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'cambios': [dato]}):
            cambios = detectar_cambios([{'numero': 'DD ÚNICA', 'texto': texto}])
        self.assertEqual({c['unidad']: c['alcance'] for c in cambios}, {'323 BIS': 'Parágrafo III', '281 QUATER': 'total'})
        for c in cambios:
            self.assertEqual(c['norma'], 'Código Penal')
            self.assertEqual(c['origen'], 'clausula')
            self.assertEqual(c['causante'], '')

    def test_incorporaciones_no_confunden_articulo_fuente_con_cinco_destinos(self):
        texto = 'ARTÍCULO 5. Se incorporan a la Ley N° 1768, de 10 de marzo de 1997 “Código Penal”, los Artículos 312 Quinquies, 312 Sexies, Artículo 318 Bis, Artículo 323 Ter y Artículo 323 Quater, con el siguiente texto:'
        dato = candidato('', operacion='incorpora', norma='Ley 1768', unidad='5')
        del dato['cita']
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'cambios': [dato]}):
            cambios = detectar_cambios([{'numero': '5', 'texto': texto}])
        self.assertEqual({c['unidad'] for c in cambios}, {'312 QUINQUIES', '312 SEXIES', '318 BIS', '323 TER', '323 QUATER'})

    def test_ley_modificatoria_historica_no_es_el_destino_actual(self):
        texto = 'ARTÍCULO 7. Se modifica el Artículo 389 Bis de la Ley N° 1970, de 25 de marzo de 1999 “Código de Procedimiento Penal”, modificada por la Ley N° 1173 de 3 de mayo de 2019, con el siguiente texto:'
        dato = candidato('', operacion='modifica', norma=texto, unidad='ARTÍCULO 7')
        del dato['cita']
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'cambios': [dato]}):
            cambios = detectar_cambios([{'numero': '7', 'texto': texto}])
        self.assertEqual([(c['norma'], c['unidad']) for c in cambios], [('Código de Procedimiento Penal', '389 BIS')])


class OperacionesMezcladasTests(SimpleTestCase):
    def test_lista_de_referencias_no_asigna_modificacion_a_articulo_derogado(self):
        texto = 'ARTÍCULO 1. Se modifica el Artículo 25 del Código Penal y se deroga el Artículo 26 del mismo Código.'
        dato = candidato('', operacion='modifica', norma='Código Penal', unidad='25')
        del dato['cita']
        with patch('modulo_catalogo.services.lectura_normativa_service.consultar', return_value={'cambios': [dato]}):
            cambios = detectar_cambios([{'numero': '1', 'texto': texto}])
        self.assertEqual([(c['operacion'], c['unidad']) for c in cambios], [('modifica', '25')])


class ReferenciasEnReglasTemporalesTests(SimpleTestCase):
    def test_mencionar_codigo_en_regla_temporal_no_lo_asigna_como_afectado(self):
        texto = 'ARTÍCULO 1. Los procedimientos previstos en el Código de Procedimiento Penal entrarán en vigencia desde su publicación.'
        c = ajustar_cambio_literal(candidato(texto, operacion='temporal'), {'numero': '1', 'texto': texto})
        self.assertEqual(c['operacion'], 'temporal')
        self.assertEqual(c['norma'], '')
        self.assertEqual(c['unidad'], '')
