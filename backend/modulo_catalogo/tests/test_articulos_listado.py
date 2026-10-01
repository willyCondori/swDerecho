"""
El listado de artículos (GET /api/catalogo/articulos/) devuelve el nombre y la
sigla de la norma, para mostrar en la columna "Norma": nombre arriba y
abreviación abajo.
"""
from rest_framework.test import APITestCase

from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho
from modulo_usuarios.tests.factories import crear_rol, crear_usuario


class ArticulosListadoNormaTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario("listado.articulos", rol=crear_rol("Abogado"))
        cls.rama = RamaDerecho.objects.create(nombre="Rama test listado")

    def setUp(self):
        self.client.force_authenticate(self.usuario)

    def _articulo_de(self, norma):
        return Articulo.objects.create(
            numero_articulo="1", titulo="Art. 1", contenido="Contenido.",
            norma=norma, rama=self.rama,
        )

    def _fila(self, articulo):
        resp = self.client.get("/api/catalogo/articulos/")
        data = resp.data["results"] if isinstance(resp.data, dict) and "results" in resp.data else resp.data
        return next(a for a in data if a["id"] == articulo.pk)

    def test_devuelve_nombre_y_sigla_de_la_norma(self):
        norma = Norma.objects.create(nombre="Ley de prueba del listado", sigla="LPL")
        fila = self._fila(self._articulo_de(norma))

        self.assertEqual(fila["norma_nombre"], "Ley de prueba del listado")
        self.assertEqual(fila["norma_sigla"], "LPL")

    def test_una_norma_sin_sigla_devuelve_solo_el_nombre(self):
        norma = Norma.objects.create(nombre="Norma sin sigla del listado")
        fila = self._fila(self._articulo_de(norma))

        self.assertEqual(fila["norma_nombre"], "Norma sin sigla del listado")
        self.assertFalse(fila["norma_sigla"])
