"""
python manage.py regenerar_embeddings_articulos --version <etiqueta>:
genera embeddings bajo una versión de modelo puntual sin tocar los de
otra versión — el mecanismo que permite tener el modelo base y el
afinado (post fine-tuning) conviviendo en la base de datos.

El modelo de Sentence Transformers real no se instala en este entorno de
tests a propósito (ver el comentario en .github/workflows/backend-tests.yml:
son cientos de MB de torch/sentence-transformers que no hacen falta para
probar la lógica de negocio), así que _obtener_modelo se mockea con un
modelo falso que devuelve vectores determinísticos.
"""
from unittest.mock import MagicMock, patch

import numpy as np
from django.core.management import call_command
from django.test import TestCase

from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho
from modulo_ia.models.embedding import EmbeddingArticulo

RUTA_OBTENER_MODELO = "modulo_catalogo.management.commands.regenerar_embeddings_articulos._obtener_modelo"


def _modelo_falso():
    """Modelo falso: .encode(lista_de_textos) -> array de vectores 768-dim determinísticos."""
    modelo = MagicMock()

    def encode(textos, **kwargs):
        return np.tile(np.linspace(0, 1, 768), (len(textos), 1))

    modelo.encode.side_effect = encode
    return modelo


class RegenerarEmbeddingsVersionTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.rama = RamaDerecho.objects.create(nombre="Rama test regenerar")
        cls.norma = Norma.objects.create(nombre="Norma test regenerar", sigla="NTR")
        cls.articulo = Articulo.objects.create(
            numero_articulo="1", titulo="Art. 1", contenido="Contenido de prueba suficientemente largo.",
            norma=cls.norma, rama=cls.rama,
        )

    def _correr(self, *args):
        with patch(RUTA_OBTENER_MODELO, return_value=_modelo_falso()):
            call_command("regenerar_embeddings_articulos", *args)

    def test_genera_con_la_version_pedida(self):
        self._correr("--modelo-version", "sw-derecho-embeddings-v1")

        emb = EmbeddingArticulo.objects.get(articulo=self.articulo)
        self.assertEqual(emb.modelo_version, "sw-derecho-embeddings-v1")

    def test_generar_una_version_nueva_no_toca_la_anterior(self):
        self._correr("--modelo-version", "modelo-base")
        emb_base = EmbeddingArticulo.objects.get(articulo=self.articulo, modelo_version="modelo-base")

        self._correr("--modelo-version", "sw-derecho-embeddings-v1")

        # Las dos versiones conviven — no se borró ni se sobrescribió la del modelo base.
        self.assertEqual(EmbeddingArticulo.objects.filter(articulo=self.articulo).count(), 2)
        emb_base.refresh_from_db()
        self.assertEqual(emb_base.modelo_version, "modelo-base")
        self.assertTrue(
            EmbeddingArticulo.objects.filter(articulo=self.articulo, modelo_version="sw-derecho-embeddings-v1").exists()
        )

    def test_correr_dos_veces_la_misma_version_actualiza_no_duplica(self):
        self._correr("--modelo-version", "sw-derecho-embeddings-v1")
        self._correr("--modelo-version", "sw-derecho-embeddings-v1")

        self.assertEqual(
            EmbeddingArticulo.objects.filter(articulo=self.articulo, modelo_version="sw-derecho-embeddings-v1").count(),
            1,
        )

    def test_sin_version_usa_la_activa_de_settings(self):
        with self.settings(EMBEDDING_MODEL_VERSION="version-activa-test"):
            self._correr()

        self.assertTrue(
            EmbeddingArticulo.objects.filter(articulo=self.articulo, modelo_version="version-activa-test").exists()
        )

    def test_solo_faltantes_respeta_la_version(self):
        self._correr("--modelo-version", "modelo-base")

        # "--solo-faltantes" para sw-derecho-embeddings-v1: el artículo NO
        # tiene embedding de esa versión (solo de "modelo-base"), así que
        # sigue contando como faltante y se genera.
        self._correr("--modelo-version", "sw-derecho-embeddings-v1", "--solo-faltantes")

        self.assertTrue(
            EmbeddingArticulo.objects.filter(articulo=self.articulo, modelo_version="sw-derecho-embeddings-v1").exists()
        )

    def test_solo_faltantes_no_regenera_si_ya_tiene_esa_version(self):
        self._correr("--modelo-version", "sw-derecho-embeddings-v1")
        emb = EmbeddingArticulo.objects.get(articulo=self.articulo, modelo_version="sw-derecho-embeddings-v1")
        vector_original = list(emb.vector)

        with patch(RUTA_OBTENER_MODELO) as mock_obtener:
            call_command("regenerar_embeddings_articulos", "--modelo-version", "sw-derecho-embeddings-v1", "--solo-faltantes")
            mock_obtener.assert_not_called()  # ni siquiera debería cargar el modelo: no hay nada que hacer

        emb.refresh_from_db()
        self.assertEqual(list(emb.vector), vector_original)
