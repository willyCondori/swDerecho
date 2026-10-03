from unittest.mock import Mock, patch

import numpy as np
from django.db import connection
from django.test import TransactionTestCase

from modulo_ia.models.chunk import ChunkCaso
from modulo_ia.models.embedding import EmbeddingChunk
from modulo_ia.services.model_loader import version_activa
from modulo_ia.tasks.analisis_task import ejecutar_analisis_caso
from modulo_casos.models.caso import Caso
from modulo_clientes.models.cliente import Cliente
from modulo_usuarios.tests.factories import crear_usuario, crear_rol


class PreparacionAnalisisTests(TransactionTestCase):
    def setUp(self):
        usuario = crear_usuario("preparar.analisis", rol=crear_rol("Abogado"))
        cliente = Cliente.objects.create(nombres="Cliente", apellidos="Preparación")
        self.caso = Caso.objects.create(
            codigo="CASO-PREPARAR", titulo="Caso", descripcion="Texto jurídico de prueba.",
            usuario=usuario, cliente=cliente,
        )
        self.previo = ChunkCaso.objects.create(caso=self.caso, contenido="Texto anterior", orden=0)
        EmbeddingChunk.objects.create(chunk=self.previo, modelo_version=version_activa(), vector=[0.1] * 768)

    def modelo(self):
        modelo = Mock()
        def encode(textos, **kwargs):
            self.assertFalse(connection.in_atomic_block)
            self.assertTrue(ChunkCaso.objects.filter(pk=self.previo.pk).exists())
            return np.ones((len(textos), 768))
        modelo.encode.side_effect = encode
        return modelo

    def test_calculo_fuera_de_transaccion_reemplaza_solo_al_publicar(self):
        with patch("modulo_ia.services.vectorizacion_service.obtener_modelo", return_value=self.modelo()):
            resultado = ejecutar_analisis_caso(self.caso.pk)
        self.assertNotIn("error", resultado)
        self.assertFalse(ChunkCaso.objects.filter(pk=self.previo.pk).exists())
        self.assertEqual(self.caso.chunks.count(), 1)

    def test_fallo_posterior_a_persistir_restaurara_analisis_anterior(self):
        with patch("modulo_ia.services.vectorizacion_service.obtener_modelo", return_value=self.modelo()), patch(
            "modulo_ia.services.ranking_service.RankingService.calcular_ranking",
            side_effect=RuntimeError("Fallo de ranking"),
        ):
            resultado = ejecutar_analisis_caso(self.caso.pk)
        self.assertIn("error", resultado)
        self.assertEqual(list(self.caso.chunks.values_list("id", flat=True)), [self.previo.pk])
        self.assertEqual(EmbeddingChunk.objects.filter(chunk=self.previo).count(), 1)
