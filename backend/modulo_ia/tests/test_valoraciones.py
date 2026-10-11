import json
import tempfile
from pathlib import Path
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient
from modulo_catalogo.models import Articulo, Norma, RamaDerecho
from modulo_casos.models.caso import Caso
from modulo_clientes.models.cliente import Cliente
from modulo_ia.models.resultado import ResultadoArticulo
from modulo_ia.models.valoracion import ValoracionArticulo
from modulo_ia.services.valoracion_service import contexto_caso
from modulo_usuarios.tests.factories import crear_usuario, crear_rol


class ValoracionesTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario('valorador', rol=crear_rol('Abogado'))
        self.client = APIClient()
        self.client.force_authenticate(self.usuario)
        self.caso = Caso.objects.create(codigo='VAL-1', titulo='Robo', descripcion='Robo a mano armada',
            usuario=self.usuario, cliente=Cliente.objects.create(nombres='A', apellidos='B'))
        self.articulo = Articulo.objects.create(norma=Norma.objects.create(nombre='Penal', sigla='CP'),
            rama=RamaDerecho.objects.create(nombre='Penal'), numero_articulo='331', contenido='Artículo 331. (Robo). Texto.')
        self.resultado = self.resultado_nuevo()
        self.url = f'/api/casos/{self.caso.public_id}/valorar_articulo/'

    def resultado_nuevo(self):
        return ResultadoArticulo.objects.create(caso=self.caso, articulo=self.articulo, posicion=1,
            modelo_version='e5_base', contexto_evaluado=contexto_caso(self.caso))

    def valorar(self, valor):
        return self.client.post(self.url, {'resultado_id': self.resultado.pk, 'valor': valor}, format='json')

    def test_valoracion_sobrevive_reanalisis_y_exporta_ultima_correccion(self):
        self.assertEqual(self.valorar('util').status_code, 200)
        self.resultado.delete()
        self.resultado = self.resultado_nuevo()
        data = self.client.get(f'/api/casos/{self.caso.public_id}/articulos/').json()
        self.assertEqual(data[0]['valoracion'], 'util')
        self.assertEqual(data[0]['coincidencias'], ['Robo'])
        self.assertEqual(self.valorar('no_util').status_code, 200)
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'datos.jsonl'
            call_command('exportar_valoraciones_articulos', salida=str(ruta))
            datos = [json.loads(linea) for linea in ruta.read_text(encoding='utf-8').splitlines()]
            self.assertEqual(len(datos), 1)
            self.assertEqual(datos[0]['valor'], 'no_util')
            self.assertEqual(datos[0]['modelo_version'], 'e5_base')
            self.assertEqual(datos[0]['descripcion'], 'Robo a mano armada')
            self.valorar('sin_valorar')
            call_command('exportar_valoraciones_articulos', salida=str(ruta))
            self.assertEqual(ruta.read_text(), '')
        self.assertEqual(ValoracionArticulo.objects.count(), 3)

    def test_contexto_editado_conserva_decision_pero_no_admite_resultado_viejo(self):
        self.valorar('util')
        self.caso.descripcion = 'Robo de minerales'
        self.caso.save(update_fields=['descripcion'])
        self.assertEqual(self.valorar('util').status_code, 409)
        self.resultado.delete()
        self.resultado = self.resultado_nuevo()
        self.assertEqual(self.client.get(f'/api/casos/{self.caso.public_id}/articulos/').json()[0]['valoracion'], 'util')
        self.assertEqual(ValoracionArticulo.objects.first().muestra['descripcion'], 'Robo a mano armada')

    def test_permisos_validacion_y_resultado_ajeno(self):
        self.assertEqual(self.valorar('incorrecto').status_code, 400)
        self.assertEqual(self.client.post(self.url, {'resultado_id': 999999, 'valor': 'util'}, format='json').status_code, 404)
        self.client.force_authenticate(crear_usuario('lector', rol=crear_rol('Asistente')))
        self.assertEqual(self.valorar('util').status_code, 403)
        self.assertEqual(ValoracionArticulo.objects.count(), 0)

    def test_otro_abogado_ve_la_decision_del_caso(self):
        self.valorar('util')
        self.client.force_authenticate(crear_usuario('otro', rol=crear_rol('Abogado')))
        self.assertEqual(self.client.get(f'/api/casos/{self.caso.public_id}/articulos/').json()[0]['valoracion'], 'util')

    def test_no_valorar_durante_analisis(self):
        self.caso.estado_analisis = 'procesando'
        self.caso.save(update_fields=['estado_analisis'])
        self.assertEqual(self.valorar('util').status_code, 409)

    def test_util_conserva_recomendacion_por_tentativa_incluso_sin_ranking(self):
        self.caso.descripcion = 'Me robaron con cuchillo, más intento de secuestro'
        self.caso.save(update_fields=['descripcion'])
        self.articulo.contenido = 'Artículo 334. (Secuestro). Texto de prueba'
        self.articulo.save(update_fields=['contenido'])
        self.resultado.contexto_evaluado = contexto_caso(self.caso)
        self.resultado.save(update_fields=['contexto_evaluado'])
        self.assertEqual(self.valorar('util').status_code, 200)
        self.assertTrue(ValoracionArticulo.objects.get(caso=self.caso).muestra['es_sugerencia'])
        for historica in [False, True]:
            if historica:
                self.resultado.delete()
            data = self.client.get(f'/api/casos/{self.caso.public_id}/articulos/').json()[0]
            self.assertEqual(data['valoracion'], 'util')
            self.assertTrue(data['es_sugerencia'])
            self.assertEqual(data['seleccion_historica'], historica)
            self.assertIn('intento de secuestro', data['motivo_recomendacion'])

    def test_util_que_sale_del_ranking_se_conserva_como_seleccion_historica(self):
        self.valorar('util')
        self.resultado.delete()
        data = self.client.get(f'/api/casos/{self.caso.public_id}/articulos/').json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['articulo']['id'], self.articulo.pk)
        self.assertTrue(data[0]['seleccion_historica'])
        self.assertFalse(data[0]['valoracion_desactualizada'])
        self.assertFalse(ResultadoArticulo.objects.filter(caso=self.caso).exists())

    def test_ampliar_no_avisa_y_cambiar_descripcion_avisa_sin_perder_seleccion(self):
        self.valorar('util')
        self.resultado.delete()
        for descripcion, aviso in [('Robo a mano armada e intento de secuestro', False), ('Una pelea entre vecinos', True)]:
            self.caso.descripcion = descripcion
            self.caso.save(update_fields=['descripcion'])
            data = self.client.get(f'/api/casos/{self.caso.public_id}/articulos/').json()
            self.assertEqual(data[0]['valoracion'], 'util')
            self.assertEqual(data[0]['valoracion_desactualizada'], aviso)
        self.assertEqual(ValoracionArticulo.objects.first().muestra['descripcion'], 'Robo a mano armada')

    def test_resultado_nuevo_no_duplica_seleccion_y_reconfirmar_quita_aviso(self):
        self.valorar('util')
        self.caso.descripcion = 'Otro contexto'
        self.caso.save(update_fields=['descripcion'])
        self.resultado.delete()
        self.resultado = self.resultado_nuevo()
        listado = lambda: self.client.get(f'/api/casos/{self.caso.public_id}/articulos/').json()
        self.assertEqual(len(listado()), 1)
        self.assertTrue(listado()[0]['valoracion_desactualizada'])
        self.assertEqual(self.valorar('util').status_code, 200)
        self.assertFalse(listado()[0]['valoracion_desactualizada'])

    def test_seleccion_historica_se_puede_descartar_y_no_admite_referencias_antiguas(self):
        self.valorar('util')
        decision = ValoracionArticulo.objects.first()
        self.resultado.delete()
        self.caso.descripcion = 'Descripción diferente'
        self.caso.save(update_fields=['descripcion'])
        resp = self.client.post(self.url, {'valoracion_id': decision.pk, 'valor': 'no_util'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.get(f'/api/casos/{self.caso.public_id}/articulos/').json(), [])
        self.assertEqual(self.client.post(self.url, {'valoracion_id': decision.pk, 'valor': 'util'}, format='json').status_code, 404)
        self.assertEqual(self.client.post(self.url, {'valor': 'util'}, format='json').status_code, 400)

    def test_reconfirmacion_historica_tras_reanalisis_usa_contexto_actual(self):
        self.valorar('util')
        decision = ValoracionArticulo.objects.first()
        self.resultado.delete()
        self.caso.descripcion = 'Robo y secuestro'
        self.caso.estado_analisis = 'completado'
        self.caso.save(update_fields=['descripcion', 'estado_analisis'])
        resp = self.client.post(self.url, {'valoracion_id': decision.pk, 'valor': 'util'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()['valoracion_desactualizada'])
        self.assertEqual(ValoracionArticulo.objects.first().muestra['descripcion'], 'Robo y secuestro')
