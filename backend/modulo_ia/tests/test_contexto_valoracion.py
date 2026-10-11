from types import SimpleNamespace
from django.test import SimpleTestCase
from modulo_ia.services.valoracion_service import conserva_relato, valoracion_desactualizada


class ContextoValoracionTests(SimpleTestCase):
    def test_ampliacion_y_cambios_de_formato(self):
        for actual in ['ME robaron con cuchillo, mas intento de secuestro',
                       'Me robaron con cuchillo.', 'Ayer: me robaron con cuchillo, luego huyeron']:
            self.assertTrue(conserva_relato('ME robaron con cuchillo', actual))

    def test_reemplazo_supresion_y_rectificacion(self):
        for actual in ['Fue una pelea entre vecinos', 'Me robaron',
                       'Me robaron con cuchillo, en realidad no me robaron',
                       'Me robaron con cuchillo, pero no usaron cuchillo']:
            self.assertFalse(conserva_relato('Me robaron con cuchillo', actual))
        self.assertTrue(conserva_relato('Me robaron con cuchillo',
                        'Me robaron con cuchillo, no lograron secuestrarme'))

    def test_fragmentos_ampliados_y_articulo_modificado(self):
        muestra = {'descripcion': 'Robo', 'fragmentos': ['Me robaron con cuchillo'], 'articulo_texto': 'Texto legal'}
        decision = SimpleNamespace(contexto_hash='anterior', muestra=muestra)
        articulo = SimpleNamespace(contenido='Texto legal')
        contexto = {'descripcion': 'Robo e intento de secuestro',
                    'fragmentos': ['Me robaron con cuchillo,', 'más intento de secuestro']}
        self.assertFalse(valoracion_desactualizada(decision, contexto, articulo))
        contexto['fragmentos'] = ['Una pelea entre vecinos']
        self.assertTrue(valoracion_desactualizada(decision, contexto, articulo))
        contexto['fragmentos'] = muestra['fragmentos']
        articulo.contenido = 'Nueva disposición'
        self.assertTrue(valoracion_desactualizada(decision, contexto, articulo))
