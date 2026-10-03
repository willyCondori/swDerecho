from unittest.mock import Mock, patch

import numpy as np
from django.db import connection
from django.test import TransactionTestCase

from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho
from modulo_catalogo.services.carga_pdf_service import cargar_articulos_desde_bytes
from modulo_ia.models.embedding import EmbeddingArticulo

SERVICIO = "modulo_catalogo.services.carga_pdf_service"


class CargaEmbeddingsLotesTests(TransactionTestCase):
    def setUp(self):
        self.norma = Norma.objects.create(nombre="Norma lote")
        self.rama = RamaDerecho.objects.create(nombre="Rama lote")
        self.articulos = [
            {"numero": str(i), "titulo": f"Art. {i}", "texto": "Texto jurídico suficiente para generar un vector."}
            for i in range(3)
        ]

    def _cargar(self, modelo, **kwargs):
        with patch(f"{SERVICIO}.extraer_texto_pdf_bytes", return_value="texto"), patch(
            f"{SERVICIO}.dividir_por_articulos", return_value=self.articulos
        ), patch(f"{SERVICIO}._obtener_modelo", return_value=modelo):
            return cargar_articulos_desde_bytes(b"pdf", self.norma.pk, self.rama.pk, **kwargs)

    def test_calcula_lote_fuera_de_transaccion_y_no_vectoriza_duplicados(self):
        Articulo.objects.create(numero_articulo="0", norma=self.norma, rama=self.rama, contenido="Anterior")
        modelo = Mock()
        def encode(textos, **kwargs):
            self.assertFalse(connection.in_atomic_block)
            self.assertEqual(len(textos), 2)
            return np.ones((len(textos), 768))
        modelo.encode.side_effect = encode
        resultado = self._cargar(modelo)
        modelo.encode.assert_called_once()
        self.assertEqual(resultado.guardados, 2)
        self.assertEqual(resultado.duplicados, 1)
        self.assertEqual(EmbeddingArticulo.objects.filter(articulo__norma=self.norma).count(), 2)

    def test_un_embedding_invalido_no_impide_guardar_los_demas(self):
        modelo = Mock()
        def encode(textos, **kwargs):
            if len(textos) > 1 or textos[0].startswith("Art. 1"):
                raise ValueError("Texto no vectorizable")
            return np.ones((1, 768))
        modelo.encode.side_effect = encode
        resultado = self._cargar(modelo)
        self.assertEqual(resultado.guardados, 3)
        self.assertEqual(len(resultado.errores_detalle), 1)
        self.assertEqual(EmbeddingArticulo.objects.filter(articulo__norma=self.norma).count(), 2)

    def test_fallo_de_publicacion_revierte_el_reemplazo(self):
        previo = Articulo.objects.create(numero_articulo="99", norma=self.norma, rama=self.rama, contenido="Anterior")
        modelo = Mock()
        modelo.encode.return_value = np.ones((3, 768))
        with patch(f"{SERVICIO}._update_task", side_effect=lambda _, progreso, __: (
            (_ for _ in ()).throw(RuntimeError("Fallo de publicación")) if progreso == 98 else None
        )):
            with self.assertRaises(RuntimeError):
                self._cargar(modelo, sobrescribir=True)
        self.assertEqual(list(Articulo.objects.filter(norma=self.norma).values_list("pk", flat=True)), [previo.pk])
