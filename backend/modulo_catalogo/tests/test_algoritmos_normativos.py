from unittest.mock import Mock, patch
from django.test import SimpleTestCase, override_settings
from django.core.cache import cache
from modulo_catalogo.services.compilaciones_service import segmentar_normas, elegir_seccion, resolver_alternativas
from modulo_catalogo.services.algoritmos_normativos_service import detectar_cambios_literales, extraer_metadatos_literales
from modulo_catalogo.services.lectura_normativa_service import extraer_unidades, localizar_clasico


class AlgoritmosNormativosTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @patch('modulo_catalogo.services.lectura_normativa_service.consultar', side_effect=AssertionError('No usar Qwen'))
    def test_compilacion_no_mezcla_codigo_con_leyes_anexas(self, modelo):
        texto = 'CÓDIGO PENAL\nDECRETO LEY N° 10426 DE 23 DE AGOSTO DE 1972\nARTÍCULO 1. Código original.\nARTÍCULO 281 Quater. Texto del Código.\nLEY N° 1333\nLEY DEL 27 DE ABRIL DE 1992\nARTÍCULO 1. Norma ambiental distinta.\nARTÍCULO 104. Delito ambiental.'
        secciones = segmentar_normas(texto, motor='clasico')
        self.assertEqual(len(secciones), 2)
        codigo, _ = elegir_seccion(texto, secciones)
        anexo, _ = elegir_seccion(texto, secciones, '1')
        self.assertNotIn('ambiental', codigo)
        self.assertNotIn('Código original', anexo)
        self.assertEqual(extraer_metadatos_literales(codigo)['numero_norma'], '10426')
        self.assertEqual(extraer_metadatos_literales(anexo)['numero_norma'], '1333')
        self.assertEqual(extraer_metadatos_literales(codigo)['fecha_norma'], '1972-08-23')
        modelo.assert_not_called()

    def test_no_segmenta_una_ley_citada_en_una_nota(self):
        texto = 'LEY N° 100\nARTÍCULO 1. Objeto.\nModificado por la Ley N° 200 de 10 de enero de 2000.\nARTÍCULO 2. Otra regla.'
        self.assertEqual(len(segmentar_normas(texto, motor='clasico')), 1)

    def test_titulos_contiguos_de_ley_y_codigo_no_crean_otra_norma(self):
        texto = 'CÓDIGO PENAL\nARTÍCULO 1. Código.\nLEY N° 2492\nCÓDIGO TRIBUTARIO BOLIVIANO\nDE 2 DE AGOSTO DE 2003\nARTÍCULO 177. Tributos.'
        ss = segmentar_normas(texto, motor='clasico')
        self.assertEqual(len(ss), 2)
        self.assertEqual(ss[1]['titulo'], 'LEY N° 2492')

    def test_no_acepta_un_identificador_de_seccion_ajeno(self):
        ss = segmentar_normas('ARTÍCULO 1. Objeto.', motor='clasico')
        with self.assertRaisesMessage(ValueError, 'no pertenece'):
            elegir_seccion('ARTÍCULO 1. Objeto.', ss, '999')

    def test_sufijos_separados_por_punto_no_se_convierten_en_repeticiones(self):
        texto = 'Artículo 13. Uno.\nArtículo 13. Quater. Dos.\nArtículo 181. Octies. Tres.\nArtículo 181. Nonies. Cuatro.'
        unidades = localizar_clasico(texto.splitlines())
        self.assertEqual([u['numero'] for u in unidades], ['13', '13 Quater', '181 Octies', '181 Nonies'])

    def test_dos_versiones_distintas_quedan_como_alternativas_sin_escoger_la_primera(self):
        unidades = [{'numero': '1', 'tipo_unidad': 'articulo', 'texto': t} for t in ['Texto anterior', 'Texto distinto']]
        resueltas, pendientes = resolver_alternativas(unidades)
        self.assertEqual(resueltas, [])
        self.assertEqual(len(pendientes), 1)
        grupo = pendientes[0]
        elegida = grupo['alternativas'][1]['id_unidad']
        resueltas, pendientes = resolver_alternativas(unidades, {grupo['clave']: elegida})
        self.assertEqual(resueltas[0]['texto'], 'Texto distinto')
        self.assertEqual(pendientes[0]['seleccionada'], elegida)

    def test_repeticion_identica_se_unifica_sin_perder_texto(self):
        u = {'numero': '1', 'texto': 'Texto íntegro original.'}
        resueltas, pendientes = resolver_alternativas([u, dict(u)])
        self.assertEqual(resueltas, [u]); self.assertEqual(pendientes, [])

    def test_alternativa_desconocida_o_objeto_invalido_no_se_acepta(self):
        u = [{'numero': '1', 'texto': texto} for texto in ['Antes', 'Después']]
        with self.assertRaises(ValueError): resolver_alternativas(u, {'articulo:1': 'inventado'})
        with self.assertRaises(ValueError): resolver_alternativas(u, [])

    @patch('modulo_catalogo.services.lectura_normativa_service.consultar', side_effect=AssertionError('No usar Qwen'))
    def test_derogacion_parcial_y_total_en_lista_1636_sin_modelo(self, modelo):
        texto = 'ÚNICA. Se derogan expresamente las siguientes disposiciones del Código Penal:\n1. El Parágrafo III del Artículo 323 Bis,\n2. El Artículo 281 Quater.'
        cambios = detectar_cambios_literales([{'numero': 'DD ÚNICA', 'tipo_unidad': 'derogatoria', 'texto': texto}])
        self.assertEqual({c['unidad']: c['alcance'] for c in cambios}, {'323 BIS': 'Parágrafo III', '281 QUATER': 'total'})
        self.assertTrue(all(c['norma'] == 'Código Penal' and c['operacion'] == 'deroga' for c in cambios))
        self.assertTrue(all(c['cita'] == texto for c in cambios))
        modelo.assert_not_called()

    def test_abrogacion_de_ley_completa_se_distingue_de_un_articulo(self):
        texto = 'TERCERA. Queda abrogada la Ley de Ejecución de Penas aprobada mediante el Decreto Ley No 11080 de 19 de diciembre de 1973, con todas sus modificaciones.'
        c = detectar_cambios_literales([{'numero': 'DF TERCERA', 'texto': texto}])[0]
        self.assertEqual((c['operacion'], c['norma'], c['unidad']), ('abroga', 'Decreto Ley 11080', ''))

    def test_reforma_no_importa_articulos_citados_como_propios(self):
        texto = 'ARTÍCULO 1. Se modifica el Artículo 25 de la Ley 260 con el siguiente texto:\n“ARTÍCULO 25. Texto de otra ley.”\nARTÍCULO 2. Se incorpora el Artículo 282Bis a la Ley 1970 con el siguiente texto:\n“ARTÍCULO 282Bis. Contenido.”\nARTÍCULO 3. Regla final.'
        u = extraer_unidades(texto, 'clasico')
        self.assertEqual([a['numero'] for a in u], ['1', '2', '3'])
        c = detectar_cambios_literales(u)
        self.assertEqual([(x['operacion'], x['unidad']) for x in c], [('modifica', '25'), ('incorpora', '282 BIS')])

    def test_referencias_pegadas_conservan_cinco_destinos_y_sufijos(self):
        texto = 'ARTÍCULO 5. Se incorporan a la Ley N° 1768 “Código Penal” los Artículos312Quinquies, 312 Sexies, Artículo318Bis, Artículo323Ter y Artículo323Quater, con el siguiente texto:\n“ARTÍCULO 312 Quinquies. Contenido.”'
        c = detectar_cambios_literales([{'numero': '5', 'texto': texto}])
        self.assertEqual({x['unidad'] for x in c}, {'312 QUINQUIES', '312 SEXIES', '318 BIS', '323 TER', '323 QUATER'})

    def test_reformas_a_ley_548_con_articulos_pegados(self):
        texto = 'ARTÍCULO 9. Se modifica los Artículos168, 169 y 170 de la Ley N° 548 con el siguiente texto:\n“ARTÍCULO 168. Primero.\nARTÍCULO 169. Segundo.”\nARTÍCULO 170. Tercero.”\nARTÍCULO 10. Objeto.'
        u = extraer_unidades(texto, 'clasico')
        self.assertNotIn('170', [a['numero'] for a in u])
        c = detectar_cambios_literales(u)
        self.assertEqual({x['unidad'] for x in c}, {'168', '169', '170'})

    def test_regla_temporal_y_general_no_inventan_derogaciones(self):
        u = [{'numero': 'DF ÚNICA', 'texto': 'ÚNICA. Se reglamentará en un plazo de noventa días.'},
             {'numero': 'DD ÚNICA', 'texto': 'ÚNICA. Quedan derogadas todas las disposiciones contrarias a esta Ley.'}]
        self.assertEqual([c['operacion'] for c in detectar_cambios_literales(u)], ['temporal', 'general'])

    def test_operaciones_mezcladas_no_asignan_destinos_del_verbo_equivocado(self):
        c = detectar_cambios_literales([{'numero': '1', 'texto': 'ARTÍCULO 1. Se modifica el Artículo 25 del Código Penal y se deroga el Artículo 26.'}])
        self.assertEqual(c[0]['operacion'], 'general')
        self.assertEqual(c[0]['unidad'], '')

    def test_nota_historica_identifica_ley_y_fecha_sin_modelo(self):
        c = detectar_cambios_literales([{'numero': '49', 'texto': 'Artículo 49. (Transferencia)\nDerogado por la Disposición Final Cuarta de la Ley 2298 de 20 de diciembre de 2001.'}])[0]
        self.assertEqual((c['origen'], c['causante'], c['fecha_causante']), ('nota_editorial', 'Ley 2298', '2001-12-20'))

    def test_cabecera_compacta_identifica_ley_1636_y_fecha(self):
        c = extraer_metadatos_literales('LEY N° 1636LEY DE 10 DE SEPTIEMBRE DE 2025\nARTÍCULO 1. Objeto.')
        self.assertEqual(c, {'tipo_norma': 'LEY', 'numero_norma': '1636', 'fecha_norma': '2025-09-10'})


class OcrLocalTests(SimpleTestCase):
    @patch('modulo_catalogo.services.pdf_normativo_service.consultar', side_effect=AssertionError('No usar Qwen'))
    @patch('modulo_catalogo.services.ocr_local_service.transcribir_pagina', return_value='ARTÍCULO 1. Texto obtenido por OCR local.')
    @patch('fitz.open')
    def test_pdf_mixto_usa_ocr_solo_para_imagenes_y_conserva_pagina_digital(self, abrir, ocr, modelo):
        digital = Mock(); digital.get_text.return_value = 'ARTÍCULO 2. Contenido digital original suficiente.'; digital.get_images.return_value = []
        imagen = Mock(); imagen.get_text.return_value = ''; imagen.get_images.return_value = [1]
        documento = Mock(is_encrypted=False); documento.__iter__ = Mock(return_value=iter([digital, imagen]))
        # Es necesario poder iterar dos veces el documento.
        documento.__iter__.side_effect = lambda: iter([digital, imagen])
        abrir.return_value.__enter__.return_value = documento
        from modulo_catalogo.services.pdf_normativo_service import leer_pdf
        texto, avisos = leer_pdf(b'pdf', 'clasico', lambda _: '')
        self.assertIn('Contenido digital original', texto)
        self.assertIn('Texto obtenido por OCR', texto)
        ocr.assert_called_once_with(imagen, 2)
        self.assertIn('OCR local', avisos[0]); modelo.assert_not_called()

    @override_settings(PDF_TESSERACT_CMD='tesseract-local', PDF_OCR_IDIOMA='spa')
    @patch('subprocess.run')
    def test_ocr_es_serial_limita_hilos_y_no_utiliza_shell(self, ejecutar):
        from modulo_catalogo.services.ocr_local_service import transcribir_pagina
        pagina = Mock(); pagina.rect.width = 600; pagina.rect.height = 900
        ejecutar.return_value = Mock(returncode=0, stdout='ARTÍCULO 1. Texto legible del documento.')
        texto = transcribir_pagina(pagina, 1)
        self.assertIn('Texto legible', texto)
        self.assertEqual(ejecutar.call_args.kwargs['env']['OMP_THREAD_LIMIT'], '1')
        self.assertNotIn('shell', ejecutar.call_args.kwargs)
        self.assertEqual(ejecutar.call_args.args[0][0], 'tesseract-local')


class RecuperacionSeccionesTests(SimpleTestCase):
    def test_recuperacion_respeta_norma_seleccionada(self):
        from types import SimpleNamespace
        from modulo_catalogo.services.disposiciones_service import recuperar_unidades_seleccionadas
        texto = ('LEY N° 100\nARTÍCULO 1. Norma principal.\nDISPOSICIÓN FINAL\n'
                 'ÚNICA. Se abroga la Ley N° 50.\nLEY N° 200\nARTÍCULO 1. Anexo.\n'
                 'DISPOSICIÓN FINAL\nÚNICA. Se abroga la Ley N° 60.')
        seccion = segmentar_normas(texto, motor='clasico')[1]
        documento = SimpleNamespace(analisis_normativo={'seccion': seccion}, norma=None)
        unidades = recuperar_unidades_seleccionadas(documento, texto)
        self.assertTrue(any('Ley N° 60' in u['texto'] for u in unidades))
        self.assertFalse(any('Ley N° 50' in u['texto'] for u in unidades))

    def test_recuperacion_no_reasigna_seccion_que_no_puede_identificar(self):
        from types import SimpleNamespace
        from modulo_catalogo.services.disposiciones_service import recuperar_unidades_seleccionadas
        documento = SimpleNamespace(analisis_normativo={'seccion': {'titulo': 'LEY N° 999'}}, norma=None)
        with self.assertRaisesMessage(ValueError, 'inequívocamente'):
            recuperar_unidades_seleccionadas(documento, 'LEY N° 100\nARTÍCULO 1. Texto.')


class ReferenciasPegadasTests(SimpleTestCase):
    def test_bis_pegado_a_de_conserva_destino_y_original(self):
        texto = 'ARTÍCULO 7. Se modifica el Artículo 389 Bisde la Ley N° 1970, Código de Procedimiento Penal, con el siguiente texto: “Artículo 389 Bis. Texto.”'
        unidades = extraer_unidades(texto, 'clasico')
        cambios = detectar_cambios_literales(unidades)
        self.assertEqual([c['unidad'] for c in cambios], ['389 BIS'])
        self.assertEqual(unidades[0]['texto'], texto)
