from unittest.mock import Mock, patch

import numpy as np
from django.test import SimpleTestCase, TestCase, override_settings

from modulo_ia.services.vectorizacion_service import vectorizar_textos
from modulo_ia.services.embedding_service import EmbeddingService
from modulo_ia.models.embedding import EmbeddingChunk
from modulo_ia.models.chunk import ChunkCaso
from modulo_casos.models.caso import Caso
from modulo_clientes.models.cliente import Cliente
from modulo_usuarios.tests.factories import crear_usuario, crear_rol


@override_settings(EMBEDDING_USE_E5_PREFIXES=False)
class VectorizacionTests(SimpleTestCase):
    @override_settings(EMBEDDING_BATCH_SIZE=8)
    def test_encode_recibe_lista_y_tamano_de_lote(self):
        modelo = Mock()
        modelo.encode.return_value = np.ones((2, 768))
        vectores = vectorizar_textos(["uno", "dos"], modelo)
        modelo.encode.assert_called_once_with(["uno", "dos"], batch_size=8, normalize_embeddings=True)
        self.assertEqual(len(vectores), 2)

    @override_settings(EMBEDDING_USE_E5_PREFIXES=True)
    def test_e5_distingue_consultas_y_documentos(self):
        modelo = Mock()
        modelo.encode.return_value = np.ones((1, 768))
        vectorizar_textos(["robo"], modelo)
        self.assertEqual(modelo.encode.call_args.args[0], ["passage: robo"])
        with patch("modulo_ia.services.vectorizacion_service.obtener_modelo", return_value=modelo):
            EmbeddingService._obtener_vector("robo")
        self.assertEqual(modelo.encode.call_args.args[0], ["query: robo"])

    def test_rechaza_dimensiones_y_valores_no_finitos(self):
        for matriz in [np.ones((1, 10)), np.full((1, 768), np.nan), np.full((1, 768), np.inf)]:
            modelo = Mock()
            modelo.encode.return_value = matriz
            with self.assertRaises(ValueError):
                vectorizar_textos(["texto"], modelo)


class PersistenciaEmbeddingsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuario = crear_usuario("embedding.lotes", rol=crear_rol("Abogado"))
        cliente = Cliente.objects.create(nombres="Cliente", apellidos="Lotes")
        caso = Caso.objects.create(codigo="CASO-LOTES", titulo="Lotes", usuario=usuario, cliente=cliente)
        cls.chunks = ChunkCaso.objects.bulk_create([
            ChunkCaso(caso=caso, contenido="texto", orden=i) for i in range(5)
        ])

    def test_upsert_por_lote_no_duplica_la_version(self):
        with patch.object(EmbeddingService, "preparar_vectores", return_value=[[0.1] * 768] * 5):
            EmbeddingService.generar_para_caso(self.chunks)
        with self.assertNumQueries(1):  # INSERT ON CONFLICT para los cinco chunks
            EmbeddingService.generar_para_caso(self.chunks, vectores=[[0.2] * 768] * 5)
        self.assertEqual(EmbeddingChunk.objects.filter(chunk__in=self.chunks).count(), 5)
        self.assertAlmostEqual(float(EmbeddingChunk.objects.get(chunk=self.chunks[0]).vector[0]), 0.2)
