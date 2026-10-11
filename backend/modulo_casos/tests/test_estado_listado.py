from django.test import SimpleTestCase
from modulo_casos.models.caso import Caso
from modulo_casos.serializers.caso_serializer import CasoListSerializer


class EstadoListadoTests(SimpleTestCase):
    def test_listado_declara_estado_persistido_sin_consultas_adicionales(self):
        serializer = CasoListSerializer()
        self.assertIn('estado_analisis', serializer.fields)
        for estado in ('pendiente', 'procesando', 'completado', 'error'):
            with self.subTest(estado=estado):
                caso = Caso(estado_analisis=estado)
                campo = serializer.fields['estado_analisis']
                self.assertEqual(campo.to_representation(campo.get_attribute(caso)), estado)
