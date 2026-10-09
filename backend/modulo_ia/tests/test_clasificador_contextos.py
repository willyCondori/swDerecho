from types import SimpleNamespace

from django.test import SimpleTestCase

from modulo_ia.services.clasificador_delito_service import ClasificadorDelitoService as Clasificador
from modulo_ia.services.chunking_service import ChunkingService
from modulo_ia.services.ranking_service import RankingService


class ClasificadorContextosTests(SimpleTestCase):
    def test_encabezados_vacios_no_son_cuerpo_normativo(self):
        for contenido in ("Artículo 62. (Revocatoria).", "Artículo 68. (Revocatoria)", "", "Artículo 61. (Periodo de Prueba)."):
            self.assertFalse(RankingService._tiene_cuerpo(SimpleNamespace(contenido=contenido)))
        self.assertTrue(RankingService._tiene_cuerpo(SimpleNamespace(contenido="Artículo 1. (Regla). Se prohíbe.")))
        self.assertTrue(RankingService._tiene_cuerpo(SimpleNamespace(contenido="Se prohíbe.")))

    def test_categoria_no_depende_de_mayusculas_del_catalogo(self):
        textos = [
            "Roboo", "Robo", "Me quitaron el celular con un cuchillo.",
            ("La persona relató los antecedentes de su jornada. " * 30)
            + "Al regresar a casa, dos sujetos la amenazaron con un cuchillo y le robaron el celular."
            + ("Luego acudió a presentar la denuncia correspondiente. " * 30),
        ]
        for texto in textos:
            for titulo in ("ROBO", "Robo", "robo", "\nRobo\n"):
                with self.subTest(texto=texto[:30], titulo=titulo):
                    articulo = SimpleNamespace(contenido=f"Artículo 331. ({titulo}). El que se apoderare...")
                    categorias = Clasificador.clasificar_texto(texto, "Penal")
                    self.assertGreater(Clasificador.score_delito_articulo(articulo, categorias, "Penal"), 0)
                    otro = SimpleNamespace(contenido="Artículo 62. (Revocatoria).")
                    self.assertEqual(Clasificador.score_delito_articulo(otro, categorias, "Penal"), 0)

    def test_relato_largo_conserva_hechos_al_final(self):
        texto = "Antecedentes del caso. " * 150 + "Me amenazaron con un cuchillo y se llevaron mi celular."
        fragmentos = ChunkingService._partir_en_fragmentos(texto)
        self.assertGreater(len(fragmentos), 1)
        self.assertTrue(any("se llevaron mi celular." in fragmento for fragmento in fragmentos))
        self.assertEqual(ChunkingService._partir_en_fragmentos("Roboo"), ["Roboo"])
