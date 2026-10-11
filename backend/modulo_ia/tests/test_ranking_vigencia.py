from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from modulo_catalogo.models import Articulo, Norma, RamaDerecho, DocumentoNorma, CambioNormativo
from modulo_casos.models.caso import Caso
from modulo_clientes.models.cliente import Cliente
from modulo_ia.models.chunk import ChunkCaso
from modulo_ia.models.embedding import EmbeddingArticulo, EmbeddingChunk
from modulo_ia.services.model_loader import version_activa
from modulo_ia.services.ranking_service import RankingService
from modulo_ia.services.figura_transversal_service import FiguraTransversalService
from modulo_usuarios.tests.factories import crear_rol, crear_usuario


class RankingVigenciaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuario = crear_usuario('ranking.vigencia', rol=crear_rol('Abogado'))
        cliente = Cliente.objects.create(nombres='Cliente', apellidos='Vigencia')
        cls.rama = RamaDerecho.objects.create(nombre='Penal ranking')
        cls.norma = Norma.objects.create(nombre='Norma ranking')
        cls.fuente = DocumentoNorma.objects.create(norma=cls.norma, nombre_original='fuente.pdf', ruta_archivo='fuente.pdf', tamano=1)
        cls.caso = Caso.objects.create(codigo='CASO-VIGENCIA', titulo='Caso vigencia', descripcion='tentativa de robo', usuario=usuario, cliente=cliente, rama_detectada=cls.rama)
        cls.vector = [1.0] + [0.0] * 767
        chunk = ChunkCaso.objects.create(caso=cls.caso, orden=0, contenido='tentativa de robo', tipo='texto')
        EmbeddingChunk.objects.create(chunk=chunk, vector=cls.vector, modelo_version=version_activa())

    def articulo(self, numero, contenido='Artículo de prueba', vector=None):
        articulo = Articulo.objects.create(norma=self.norma, rama=self.rama, numero_articulo=str(numero), contenido=contenido)
        EmbeddingArticulo.objects.create(articulo=articulo, vector=vector or self.vector, modelo_version=version_activa())
        return articulo

    def cambio(self, articulo=None, **kwargs):
        datos = dict(fuente=self.fuente, norma_afectada=self.norma, articulo_afectado=articulo,
                     operacion='deroga', estado_revision='confirmado', fecha_efecto=timezone.localdate() - timedelta(days=1),
                     referencia={'alcance': 'total', 'parte_afectada': {'tipo': 'total'}}, cita='Se deroga.', huella=f'cambio-{CambioNormativo.objects.count()}')
        datos.update(kwargs)
        return CambioNormativo.objects.create(**datos)

    def test_derogacion_total_se_excluye_antes_del_limite_de_candidatos(self):
        for numero in range(51):
            self.cambio(self.articulo(numero))
        vigente = self.articulo(100)
        scores, _ = RankingService._score_semantico_por_articulo(self.caso)
        self.assertEqual(set(scores), {vigente.pk})

    def test_abrogacion_de_norma_y_restauracion(self):
        articulo = self.articulo(1)
        cambio = self.cambio(operacion='abroga')
        self.assertEqual(dict(RankingService._score_semantico_por_articulo(self.caso)[0]), {})
        cambio.estado_revision = 'revertido'
        cambio.save(update_fields=['estado_revision'])
        self.assertIn(articulo.pk, RankingService._score_semantico_por_articulo(self.caso)[0])

    def test_parciales_pendientes_descartadas_y_futuras_se_conservan(self):
        for i, cambios in enumerate([
            {'referencia': {'alcance': 'Parágrafo II', 'parte_afectada': {'tipo': 'parcial'}}},
            {'estado_revision': 'pendiente'}, {'estado_revision': 'descartado'},
            {'fecha_efecto': timezone.localdate() + timedelta(days=2)},
        ]):
            with self.subTest(cambios=cambios):
                articulo = self.articulo(i)
                self.cambio(articulo, **cambios)
                self.assertIn(articulo.pk, RankingService._score_semantico_por_articulo(self.caso)[0])

    def test_las_figuras_transversales_respetan_la_misma_vigencia(self):
        derogado = self.articulo(1, 'Artículo 1. (TENTATIVA). Texto de prueba')
        parcial = self.articulo(2, 'Artículo 2. (TENTATIVA). Texto conservado')
        self.cambio(derogado)
        self.cambio(parcial, referencia={'alcance': 'Parágrafo II', 'parte_afectada': {'tipo': 'parcial'}})
        encontrados = FiguraTransversalService.articulos_por_figuras({'TENTATIVA'}, self.rama.pk)
        self.assertEqual([a.pk for a in encontrados], [parcial.pk])

    def test_sugerencias_se_conservan_aunque_haya_quince_principales(self):
        for numero in range(16):
            self.articulo(numero)
        vector = [0.45, (1 - 0.45 ** 2) ** 0.5] + [0.0] * 766
        sugerencia = self.articulo(99, 'Artículo 99. (TENTATIVA). Texto de prueba', vector)
        # Evita depender del diccionario de delitos en esta prueba del cupo.
        with patch('modulo_ia.services.ranking_service.ClasificadorDelitoService.score_delito_articulo', return_value=0):
            resultados = RankingService.calcular_ranking(self.caso)
        self.assertEqual(sum(not r.es_sugerencia for r in resultados), 15)
        self.assertEqual([r.articulo_id for r in resultados if r.es_sugerencia], [sugerencia.pk])
        self.assertEqual(resultados[-1].posicion, 16)

    def valorar(self, articulo, valor):
        from modulo_ia.models.valoracion import ValoracionArticulo
        return ValoracionArticulo.objects.create(
            caso=self.caso, articulo=articulo, usuario=self.caso.usuario,
            valor=valor, contexto_hash='0' * 64, muestra={})

    def test_robo_principal_y_secuestro_complementario_por_tentativa(self):
        self.caso.chunks.update(contenido='Me robaron con cuchillo, más intento de secuestro')
        robo = self.articulo(331, 'Artículo 331. (Robo). Texto de prueba')
        secuestro = self.articulo(334, 'Artículo 334. (Secuestro). Texto de prueba')
        with patch('modulo_ia.services.ranking_service.ClasificadorDelitoService.score_delito_articulo', return_value=1):
            resultados = RankingService.calcular_ranking(self.caso)
        por_articulo = {r.articulo_id: r for r in resultados}
        self.assertFalse(por_articulo[robo.pk].es_sugerencia)
        self.assertTrue(por_articulo[secuestro.pk].es_sugerencia)
        self.assertLess(por_articulo[robo.pk].posicion, por_articulo[secuestro.pk].posicion)

    def test_no_util_se_excluye_antes_del_limite_semantico(self):
        for numero in range(51):
            self.valorar(self.articulo(numero), 'no_util')
        disponible = self.articulo(100)
        scores, _ = RankingService._score_semantico_por_articulo(self.caso)
        self.assertEqual(set(scores), {disponible.pk})

    def test_no_util_excluye_principales_y_sugerencias_al_reanalizar(self):
        principal = self.articulo(1)
        vector = [0.45, (1 - 0.45 ** 2) ** 0.5] + [0.0] * 766
        sugerencia = self.articulo(99, 'Artículo 99. (TENTATIVA). Texto de prueba', vector)
        with patch('modulo_ia.services.ranking_service.ClasificadorDelitoService.score_delito_articulo', return_value=0):
            iniciales = RankingService.calcular_ranking(self.caso)
            self.assertEqual({r.articulo_id for r in iniciales}, {principal.pk, sugerencia.pk})
            self.valorar(principal, 'no_util')
            self.valorar(sugerencia, 'no_util')
            self.assertEqual(RankingService.calcular_ranking(self.caso), [])
        self.assertFalse(self.caso.resultado_articulos.exists())

    def test_ultima_decision_rehabilita_sin_afectar_otros_casos(self):
        articulo = self.articulo(1)
        decision = self.valorar(articulo, 'no_util')
        otro = Caso.objects.create(codigo='OTRO-UTIL', titulo='Otro', usuario=self.caso.usuario,
                                  cliente=self.caso.cliente, rama_detectada=self.rama)
        chunk = ChunkCaso.objects.create(caso=otro, orden=0, contenido='robo', tipo='texto')
        EmbeddingChunk.objects.create(chunk=chunk, vector=self.vector, modelo_version=version_activa())
        self.assertIn(articulo.pk, RankingService._score_semantico_por_articulo(otro)[0])
        for valor in ['util', 'sin_valorar']:
            self.valorar(articulo, valor)
            self.assertIn(articulo.pk, RankingService._score_semantico_por_articulo(self.caso)[0])
            self.valorar(articulo, 'no_util')
            self.assertNotIn(articulo.pk, RankingService._score_semantico_por_articulo(self.caso)[0])
        self.assertTrue(type(decision).objects.filter(pk=decision.pk).exists())

    def test_no_util_persiste_tras_editar_y_excluye_proteccion_complementaria(self):
        articulo = self.articulo(1)
        self.valorar(articulo, 'no_util')
        self.caso.descripcion = 'Descripción nueva del mismo caso'
        self.caso.save(update_fields=['descripcion'])
        with patch('modulo_ia.services.ranking_service.ProteccionMenoresService.hay_menores', return_value=True), \
             patch('modulo_ia.services.ranking_service.ProteccionMenoresService.articulos', return_value=[articulo]):
            self.assertEqual(RankingService.calcular_ranking(self.caso), [])
