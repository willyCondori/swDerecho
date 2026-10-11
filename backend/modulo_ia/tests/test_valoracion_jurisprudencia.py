from django.test import TestCase
from rest_framework.test import APIClient
from modulo_casos.models.caso import Caso
from modulo_clientes.models.cliente import Cliente
from modulo_ia.models.jurisprudencia import ResolucionJurisprudencia, ResultadoJurisprudencia, FragmentoJurisprudencia, EmbeddingJurisprudencia
from modulo_ia.models.valoracion import ValoracionJurisprudencia
from modulo_ia.models.chunk import ChunkCaso
from modulo_ia.models.embedding import EmbeddingChunk
from modulo_ia.services.valoracion_service import contexto_caso
from modulo_ia.services.valoracion_jurisprudencia_service import excluidas
from modulo_ia.services.jurisprudencia_service import JurisprudenciaService
from modulo_ia.services.model_loader import version_activa
from modulo_usuarios.tests.factories import crear_usuario, crear_rol

TEXTO = 'El Tribunal examinó los elementos del delito de robo agravado y estableció la aplicación del artículo 332 del Código Penal.'
VECTOR = [1.] + [0.] * 767


class ValoracionJurisprudenciaTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario('val.juris', rol=crear_rol('Abogado'))
        self.client = APIClient()
        self.client.force_authenticate(self.usuario)
        self.caso = Caso.objects.create(codigo='VJ-1', titulo='Robo', descripcion='Me robaron con cuchillo',
            estado_analisis='completado', usuario=self.usuario, cliente=Cliente.objects.create(nombres='A', apellidos='B'))
        self.resolucion = ResolucionJurisprudencia.objects.create(fuente_id='99001', numero='AS/1/2024', texto=TEXTO,
            huella='a' * 64, url_fuente='https://apigenesis.tsj.bo/api/v1/resoluciones/99001')
        self.resultado = self.nuevo_resultado()
        self.url = f'/api/casos/{self.caso.public_id}/valorar_jurisprudencia/'
        self.listado = f'/api/casos/{self.caso.public_id}/jurisprudencia/'

    def nuevo_resultado(self):
        return ResultadoJurisprudencia.objects.create(caso=self.caso, resolucion=self.resolucion,
            posicion=1, score_semantico=.8, modelo_version=version_activa(), fragmento=TEXTO,
            huella_fuente=self.resolucion.huella, contexto_evaluado=contexto_caso(self.caso), es_sugerencia=True)

    def valorar(self, valor, **ids):
        return self.client.post(self.url, {**(ids or {'resultado_id': self.resultado.pk}), 'valor': valor}, format='json')

    def filas(self):
        return self.client.get(self.listado).json()['resultados']

    def test_util_sobrevive_al_cambio_de_resultado_y_conserva_recomendacion(self):
        self.assertEqual(self.valorar('util').status_code, 200)
        self.resultado.delete()
        self.resultado = self.nuevo_resultado()
        fila = self.filas()[0]
        self.assertEqual(fila['valoracion'], 'util')
        self.assertTrue(fila['es_sugerencia'])
        self.assertFalse(fila['valoracion_desactualizada'])
        self.assertEqual(ValoracionJurisprudencia.objects.get().muestra['resultado']['fragmento'], TEXTO)

    def test_util_fuera_del_ranking_se_conserva_y_se_puede_confirmar(self):
        self.valorar('util')
        self.resultado.delete()
        fila = self.filas()[0]
        self.assertTrue(fila['seleccion_historica'])
        self.caso.descripcion = 'Una pelea entre vecinos'
        self.caso.save(update_fields=['descripcion'])
        self.assertTrue(self.filas()[0]['valoracion_desactualizada'])
        respuesta = self.valorar('util', valoracion_id=fila['valoracion_id'])
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.assertFalse(self.filas()[0]['valoracion_desactualizada'])
        self.assertEqual(ValoracionJurisprudencia.objects.count(), 2)

    def test_ampliar_relato_no_desactualiza_y_cambiarlo_si(self):
        self.valorar('util')
        for descripcion, aviso in [('Me robaron con cuchillo e intento de secuestro', False), ('Una pelea entre vecinos', True)]:
            self.caso.descripcion = descripcion
            self.caso.save(update_fields=['descripcion'])
            self.assertEqual(self.filas()[0]['valoracion_desactualizada'], aviso)

    def test_no_util_se_excluye_en_ambas_busquedas_y_se_puede_restaurar(self):
        fragmento = FragmentoJurisprudencia.objects.create(resolucion=self.resolucion, orden=0, contenido=TEXTO)
        EmbeddingJurisprudencia.objects.create(fragmento=fragmento, vector=VECTOR, modelo_version=version_activa())
        chunk = ChunkCaso.objects.create(caso=self.caso, orden=0, contenido=self.caso.descripcion)
        EmbeddingChunk.objects.create(chunk=chunk, vector=VECTOR, modelo_version=version_activa())
        self.assertEqual(len(JurisprudenciaService.recuperar(self.caso)), 1)
        self.assertEqual(self.valorar('no_util').status_code, 200)
        self.assertEqual(JurisprudenciaService.recuperar(self.caso), [])
        self.resultado.delete()
        descartada = self.filas()[0]
        self.assertEqual(descartada['valoracion'], 'no_util')
        self.assertEqual(self.valorar('sin_valorar', valoracion_id=descartada['valoracion_id']).status_code, 200)
        self.assertEqual(excluidas(self.caso), [])
        self.assertEqual(len(JurisprudenciaService.recuperar(self.caso)), 1)

    def test_no_util_no_se_extiende_a_otros_casos(self):
        self.valorar('no_util')
        otro = Caso.objects.create(codigo='VJ-2', titulo='Otro robo', cliente=self.caso.cliente, usuario=self.usuario)
        self.assertEqual(excluidas(otro), [])

    def test_rechaza_valoraciones_de_lectores_y_resultados_de_otro_caso(self):
        self.assertEqual(self.valorar('invalido').status_code, 400)
        self.assertEqual(self.valorar('util', resultado_id=self.resultado.pk, valoracion_id=1).status_code, 400)
        otro = Caso.objects.create(codigo='VJ-3', titulo='Otro robo', cliente=self.caso.cliente, usuario=self.usuario)
        respuesta = self.client.post(f'/api/casos/{otro.public_id}/valorar_jurisprudencia/',
            {'resultado_id': self.resultado.pk, 'valor': 'util'}, format='json')
        self.assertEqual(respuesta.status_code, 404)
        self.client.force_authenticate(crear_usuario('lector.juris', rol=crear_rol('Asistente')))
        self.assertEqual(self.valorar('util').status_code, 403)
        self.assertEqual(ValoracionJurisprudencia.objects.count(), 0)

    def test_procesando_o_contexto_anterior_no_admiten_confirmar_util(self):
        self.caso.estado_analisis = 'procesando'
        self.caso.save(update_fields=['estado_analisis'])
        self.assertEqual(self.valorar('util').status_code, 409)
        self.caso.estado_analisis = 'completado'
        self.caso.descripcion = 'Una pelea entre vecinos'
        self.caso.save(update_fields=['estado_analisis', 'descripcion'])
        self.assertEqual(self.valorar('util').status_code, 409)

    def test_fuente_cambiada_avisa_y_no_confirma_fragmento_viejo(self):
        self.valorar('util')
        self.resolucion.huella = 'b' * 64
        self.resolucion.save()
        self.assertTrue(self.filas()[0]['valoracion_desactualizada'])
        self.assertTrue(self.filas()[0]['desactualizada'])
        self.assertEqual(self.valorar('util').status_code, 409)

    def test_seleccion_historica_antigua_no_sobrescribe_decision_mas_reciente(self):
        self.valorar('util')
        antigua = ValoracionJurisprudencia.objects.get().pk
        self.resultado.delete()
        self.assertEqual(self.valorar('no_util', valoracion_id=antigua).status_code, 200)
        self.assertEqual(self.valorar('util', valoracion_id=antigua).status_code, 404)
