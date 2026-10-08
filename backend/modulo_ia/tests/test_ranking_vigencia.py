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
