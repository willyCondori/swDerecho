from django.test import SimpleTestCase
from modulo_ia.services.jurisprudencia_relevancia import contexto_busqueda, evaluar_fragmento


class RelevanciaTests(SimpleTestCase):
    def test_consumacion_afirmada_no_se_interpreta_como_tentativa(self):
        _, figuras = contexto_busqueda('El secuestro se consumó y se obtuvo el rescate')
        self.assertNotIn('Tentativa', figuras)

    def evaluar(self, texto, score=.55):
        grupos, figuras = contexto_busqueda('Me robaron con cuchillo e intento de secuestro')
        return evaluar_fragmento(texto, score, grupos, figuras, .65, .50)

    def test_robo_de_menor_confianza_se_presenta_como_recomendacion(self):
        resultado = self.evaluar('El Tribunal examinó los elementos del delito de robo agravado y estableció la aplicación del artículo 332 del Código Penal.')
        self.assertTrue(resultado[1])
        self.assertIn('Robo', resultado[2])

    def test_no_recupera_objetos_ni_texto_generico_solo_por_score(self):
        for texto in ['El Tribunal examinó el acta de secuestro de hoja de coca y las pruebas documentales ofrecidas durante la audiencia de apelación.',
                      'Se secuestraron vehículos y motos, sin indicar a qué persona correspondían. El Tribunal estableció los requisitos de valoración probatoria.',
                      'El teléfono secuestrado a su persona no tenía llamadas. El Tribunal examinó la prueba y estableció los requisitos de valoración probatoria.',
                      'El Tribunal estableció que el recurso presentado debía cumplir los requisitos formales antes de su admisión y examen de fondo.']:
            self.assertIsNone(self.evaluar(texto))

    def test_descarta_caratula_aunque_tenga_todos_los_delitos(self):
        self.assertIsNone(self.evaluar('TRIBUNAL SUPREMO DE JUSTICIA\nSALA PENAL SEGUNDA\nAUTO SUPREMO 115\nPartes: Ministerio Público contra A y B\nDelito: Robo agravado, tentativa y secuestro.', .90))

    def test_secuestro_personas_y_tentativa_se_conservan_con_advertencia(self):
        resultado = self.evaluar('El Tribunal estableció que la víctima fue devuelta después de consumarse el secuestro y que no correspondía aplicar el desistimiento.')
        self.assertTrue(resultado[1])
        self.assertIn('Secuestro de personas', resultado[2])
        self.assertIn('Tentativa', resultado[2])

    def test_umbral_inferior_sigue_excluyendo_ruido(self):
        self.assertIsNone(self.evaluar('El Tribunal examinó los elementos del delito de robo agravado y estableció la aplicación del artículo 332 del Código Penal.', .49))

    def test_amenaza_de_asalto_futuro_no_se_presenta_como_robo(self):
        texto = ('La víctima fue intimidada con la amenaza de cortársele la cara y de ser atacada por maleantes. '
                 'Si se proponen, podría materializar dicha amenaza, es decir podría llegar a cortarle la cara y/o ser asaltada. '
                 'El Tribunal concluyó que la Sentencia cuenta con fundamentación analítica y apreciación de la prueba en su conjunto.')
        self.assertIsNone(self.evaluar(texto, .90))

    def test_robo_agravado_con_dinero_secuestrado_no_se_etiqueta_secuestro_personal(self):
        texto = ('CONSIDERANDO: El Tribunal declara culpables a los acusados por el delito de robo agravado, '
                 'previsto por el artículo 332. Dispone con relación a la suma de 7.500 dólares americanos, '
                 'secuestrados, la devolución a la persona propietaria.')
        resultado = self.evaluar(texto, .80)
        self.assertIn('Robo', resultado[2])
        self.assertNotIn('Secuestro de personas', resultado[2])

    def test_revision_de_sentencia_generica_se_descarta_aunque_el_score_sea_alto(self):
        texto = ('CONSIDERANDO: La revisión de sentencia es un medio legítimo para impugnar una sentencia firme '
                 'con autoridad de cosa juzgada, siempre que el recurrente demuestre errores de los jueces con nuevas pruebas.')
        self.assertIsNone(self.evaluar(texto, .95))

    def test_asalto_real_se_conserva_aunque_se_mencionen_amenazas(self):
        texto = ('La víctima recibió amenazas y fue asaltada con un cuchillo. El Tribunal examinó las pruebas '
                 'y estableció los elementos jurídicos de la conducta y la participación de los acusados.')
        self.assertIn('Robo', self.evaluar(texto, .80)[2])
