from types import SimpleNamespace
from django.test import SimpleTestCase
from modulo_ia.services.contexto_tentativa_service import ContextoTentativaService


class ContextoTentativaTests(SimpleTestCase):
    def articulo(self, titulo):
        return SimpleNamespace(titulo=titulo, contenido=f'Artículo. ({titulo}). Texto')

    def test_tentativa_explicita_y_variantes(self):
        for texto in ['Me robaron con cuchillo, más intento de secuestro',
                      'Intentaron secuestrarme', 'Trataron de secuestrarme',
                      'No lograron secuestrarme', 'Tentativa de secuestro']:
            with self.subTest(texto=texto):
                self.assertIn('sin asumir', ContextoTentativaService.motivo(self.articulo('Secuestro'), texto))

    def test_no_generaliza_a_robo_delito_consumado_negacion_o_hipotesis(self):
        self.assertEqual(ContextoTentativaService.motivo(self.articulo('Robo agravado'),
                         'Me robaron con cuchillo, más intento de secuestro'), '')
        for texto in ['Me secuestraron', 'Intentaron robarme y me secuestraron',
                      'No hubo intento de secuestro', 'Sin tentativa de secuestro',
                      'No intentaron secuestrarme', 'Podrían intentar secuestrarme']:
            with self.subTest(texto=texto):
                self.assertEqual(ContextoTentativaService.motivo(self.articulo('Secuestro'), texto), '')

    def test_distingue_secuestro_procesal_y_trata(self):
        texto = 'Robo con cuchillo e intento de secuestro'
        self.assertIn('objetos', ContextoTentativaService.motivo(self.articulo('Procedimiento para el secuestro'), texto))
        self.assertIn('hechos adicionales', ContextoTentativaService.motivo(self.articulo('Trata de personas'), texto))
