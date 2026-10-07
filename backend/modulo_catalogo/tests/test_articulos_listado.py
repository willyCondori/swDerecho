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

    def test_filtro_numero_exacto_no_confunde_2_con_20_o_2_bis(self):
        norma = Norma.objects.create(nombre='Norma filtro número')
        for numero in ['2', '20', '2 bis']:
            Articulo.objects.create(numero_articulo=numero, norma=norma, rama=self.rama, contenido='Texto completo.')
        respuesta = self.client.get('/api/catalogo/articulos/', {'numero_articulo': '2'})
        self.assertEqual([a['numero_articulo'] for a in respuesta.data['results']], ['2'])

    def test_una_norma_sin_sigla_devuelve_solo_el_nombre(self):
        norma = Norma.objects.create(nombre="Norma sin sigla del listado")
        fila = self._fila(self._articulo_de(norma))

        self.assertEqual(fila["norma_nombre"], "Norma sin sigla del listado")
        self.assertFalse(fila["norma_sigla"])

    def test_listado_compacto_no_trae_texto_completo_ni_consulta_entidades(self):
        norma = Norma.objects.create(nombre="Norma preview")
        articulo = self._articulo_de(norma)
        articulo.contenido = "Texto legal extenso. " * 200
        articulo.save(update_fields=["contenido"])
        with self.assertNumQueries(2):
            resp = self.client.get("/api/catalogo/articulos/", {"norma_id": norma.pk, "compacto": "true"})
        fila = resp.data["results"][0]
        self.assertNotIn("contenido", fila)
        self.assertEqual(fila["contenido_preview"], articulo.contenido[:360])
        detalle = self.client.get(f"/api/catalogo/articulos/{articulo.pk}/")
        self.assertEqual(detalle.data["contenido"], articulo.contenido)

    def test_filtros_por_norma_y_rama_son_paginados(self):
        norma = Norma.objects.create(nombre="Norma paginada")
        for numero in range(4):
            Articulo.objects.create(numero_articulo=str(numero), contenido="Contenido.", norma=norma, rama=self.rama)
        for accion, filtro in [("por_norma", {"norma_id": norma.pk}), ("por_rama", {"rama_id": self.rama.pk})]:
            resp = self.client.get(f"/api/catalogo/articulos/{accion}/", {**filtro, "page_size": 2})
            self.assertEqual(resp.data["count"], 4)
            self.assertEqual(len(resp.data["results"]), 2)
            self.assertIsNotNone(resp.data["next"])
