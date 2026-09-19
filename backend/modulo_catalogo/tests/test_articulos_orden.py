"""
El listado de artículos ordena por número en orden natural (1, 2, 9, 10, 100)
y no alfabético (1, 10, 100, 2, 9).
"""
from rest_framework.test import APITestCase

from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho
from modulo_usuarios.tests.factories import crear_rol, crear_usuario

URL = "/api/catalogo/articulos/"


class ArticulosOrdenNaturalTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario("orden.articulos", rol=crear_rol("Abogado"))
        cls.rama = RamaDerecho.objects.create(nombre="Rama test orden")
        cls.norma = Norma.objects.create(nombre="Norma test orden", sigla="NTO")
        # A propósito desordenados y con casos raros.
        for numero in ["100", "10", "2", "1", "9", "10 bis", "A-1", "11"]:
            Articulo.objects.create(
                numero_articulo=numero, titulo=f"Art. {numero}", contenido="Contenido.",
                norma=cls.norma, rama=cls.rama, frecuencia_historica=0,
            )

    def setUp(self):
        self.client.force_authenticate(self.usuario)

    def _numeros(self, **params):
        resp = self.client.get(URL, {"norma_id": self.norma.pk, **params})
        self.assertEqual(resp.status_code, 200)
        data = resp.data["results"] if isinstance(resp.data, dict) and "results" in resp.data else resp.data
        return [a["numero_articulo"] for a in data]

    def test_orden_por_defecto_es_numerico(self):
        self.assertEqual(
            self._numeros(),
            ["1", "2", "9", "10", "10 bis", "11", "100", "A-1"],
        )

    def test_ordenar_por_numero_ascendente(self):
        self.assertEqual(
            self._numeros(ordering="numero_articulo"),
            ["1", "2", "9", "10", "10 bis", "11", "100", "A-1"],
        )

    def test_ordenar_por_numero_descendente(self):
        self.assertEqual(
            self._numeros(ordering="-numero_articulo"),
            ["100", "11", "10 bis", "10", "9", "2", "1", "A-1"],
        )

    def test_otro_criterio_desempata_por_numero_natural(self):
        # Todos tienen la misma frecuencia: el desempate debe ser el número.
        self.assertEqual(
            self._numeros(ordering="-frecuencia_historica"),
            ["1", "2", "9", "10", "10 bis", "11", "100", "A-1"],
        )

    def test_por_norma_tambien_sale_en_orden_numerico(self):
        resp = self.client.get(f"{URL}por_norma/", {"norma_id": self.norma.pk})
        numeros = [a["numero_articulo"] for a in resp.data]
        self.assertEqual(numeros, ["1", "2", "9", "10", "10 bis", "11", "100", "A-1"])
