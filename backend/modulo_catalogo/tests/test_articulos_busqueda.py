"""
Búsqueda en el listado de artículos (GET /api/catalogo/articulos/?search=...).

Escribir "art 2" o "artículo 2" debe traer el artículo número 2 (de cada
norma), no cualquier artículo que contenga un "2" en su texto (Art. 12,
Art. 20, ...). El resto de búsquedas sigue siendo por texto.
"""
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from modulo_catalogo.busqueda import numero_articulo_buscado
from modulo_catalogo.models.articulo import Articulo
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.rama import RamaDerecho
from modulo_usuarios.tests.factories import crear_rol, crear_usuario


class NumeroArticuloBuscadoTests(SimpleTestCase):

    def test_reconoce_las_formas_de_escribir_un_articulo(self):
        for texto in [
            "art 2", "art. 2", "art.2", "Art 2", "ART. 2", "arts 2",
            "artículo 2", "articulo 2", "Artículo 2", "ARTICULO 2",
            "art. n° 2", "artículo 2°", "  art   2  ",
        ]:
            with self.subTest(texto=texto):
                self.assertEqual(numero_articulo_buscado(texto), "2")

    def test_quita_ceros_a_la_izquierda(self):
        self.assertEqual(numero_articulo_buscado("art 02"), "2")

    def test_numeros_de_varios_digitos(self):
        self.assertEqual(numero_articulo_buscado("artículo 361"), "361")

    def test_texto_normal_no_es_una_referencia(self):
        for texto in [
            "", "2", "usura", "artículo", "art", "artículo 2 del código",
            "el artículo 2", "art 2 bis", "art 2 3", "partículas 2",
        ]:
            with self.subTest(texto=texto):
                self.assertIsNone(numero_articulo_buscado(texto))


class ArticulosBusquedaTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario("busqueda.articulos", rol=crear_rol("Abogado"))
        cls.rama = RamaDerecho.objects.create(nombre="Rama test búsqueda")
        cls.norma_a = Norma.objects.create(nombre="Norma A búsqueda", sigla="NAB")
        cls.norma_b = Norma.objects.create(nombre="Norma B búsqueda", sigla="NBB")

        for numero in ["1", "2", "12", "20", "102"]:
            cls._crear(numero, cls.norma_a)
        cls._crear("2", cls.norma_b)
        # Artículo 3 de la norma A que cita al artículo 2 en su texto.
        Articulo.objects.create(
            numero_articulo="3", titulo="Art. 3 - USURA",
            contenido="Art. 3.- (USURA). Se aplica lo dispuesto en el artículo 2 de esta ley.",
            norma=cls.norma_a, rama=cls.rama,
        )

    @classmethod
    def _crear(cls, numero, norma):
        return Articulo.objects.create(
            numero_articulo=numero, titulo=f"Art. {numero}",
            contenido=f"Art. {numero}.- Contenido del artículo {numero}.",
            norma=norma, rama=cls.rama,
        )

    def setUp(self):
        self.client.force_authenticate(self.usuario)

    def _buscar(self, texto):
        resp = self.client.get("/api/catalogo/articulos/", {"search": texto})
        self.assertEqual(resp.status_code, 200)
        data = resp.data["results"] if isinstance(resp.data, dict) and "results" in resp.data else resp.data
        return [(a["norma_sigla"], a["numero_articulo"]) for a in data]

    def test_articulo_2_trae_solo_el_articulo_2_de_cada_norma(self):
        esperado = [("NAB", "2"), ("NBB", "2")]
        for texto in ["articulo 2", "artículo 2", "art 2", "Art. 2", "ART.2"]:
            with self.subTest(texto=texto):
                self.assertEqual(sorted(self._buscar(texto)), esperado)

    def test_no_trae_articulos_que_solo_contienen_un_2(self):
        resultado = self._buscar("art 2")
        for numero in ["12", "20", "102"]:
            self.assertNotIn(("NAB", numero), resultado)

    def test_no_trae_articulos_que_solo_citan_al_articulo_2(self):
        self.assertNotIn(("NAB", "3"), self._buscar("artículo 2"))

    def test_busqueda_por_texto_sigue_funcionando(self):
        self.assertEqual(self._buscar("usura"), [("NAB", "3")])

    def test_busqueda_por_texto_con_varias_palabras(self):
        self.assertEqual(self._buscar("artículo 2 de esta ley"), [("NAB", "3")])

    def test_articulo_inexistente_devuelve_lista_vacia(self):
        self.assertEqual(self._buscar("art 999"), [])
