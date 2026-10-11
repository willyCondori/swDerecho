from types import SimpleNamespace
from django.test import SimpleTestCase
from modulo_ia.services.relacion_articulos_service import relaciones_articulo


class RelacionArticulosTests(SimpleTestCase):
    def relacion(self, titulo, contenido, descripcion='', fragmentos=None):
        return relaciones_articulo(SimpleNamespace(titulo=titulo, contenido=contenido),
                                  {'descripcion': descripcion, 'fragmentos': fragmentos or []})

    def test_robo_agravado_y_sin_relacion_expresa(self):
        self.assertEqual(self.relacion('Robo agravado', 'Si el robo fuere cometido con armas.',
                                      'Me robaron con cuchillo'), ['Robo'])
        self.assertEqual(self.relacion('Trata de Personas', 'Captación de personas.',
                                      'Me robaron con cuchillo, intento de secuestro'), [])

    def test_secuestro_de_objetos_no_se_etiqueta_como_personas(self):
        self.assertEqual(self.relacion('Secuestro', 'El secuestro de objetos y documentos.',
                                      'Intentaron secuestrarme'), [])
        self.assertEqual(self.relacion('Secuestro', 'Secuestrar a una persona para obtener rescate.',
                                      'Intentaron secuestrarme'), ['Secuestro de personas'])

    def test_tentativa_y_contexto_pdf(self):
        self.assertEqual(self.relacion('Tentativa', 'Quien inicia la ejecución del delito.',
                                      fragmentos=['Intentaron secuestrarme']), ['Tentativa'])
        self.assertEqual(self.relacion('Robo', 'Robo consumado.', 'Intentaron robarme'), ['Robo'])
