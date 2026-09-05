import numpy as np
from django.test import TestCase

from modulo_usuarios.models.rol import Rol
from modulo_usuarios.models.usuario import Usuario
from modulo_clientes.models.cliente import Cliente
from modulo_catalogo.models.rama import RamaDerecho
from modulo_catalogo.models.norma import Norma
from modulo_catalogo.models.jerarquia import jerarquia as Jerarquia
from modulo_catalogo.models.articulo import Articulo, ArticuloEntidad
from modulo_catalogo.models.entidad import EntidadJuridica
from modulo_ia.models.embedding import EmbeddingArticulo, EmbeddingChunk, EntidadDetectadaCaso
from modulo_ia.models.chunk import ChunkCaso
from modulo_casos.models.caso import Caso
from modulo_ia.services.ranking_service import RankingService


def _vector_bloque(bloque: int, dim: int = 768, n_bloques: int = 3, seed: int = 0) -> list:
    """Vector unitario concentrado en un bloque de dimensiones, ~ortogonal a los otros bloques."""
    rng = np.random.default_rng(seed)
    v = np.zeros(dim)
    ancho = dim // n_bloques
    v[bloque * ancho:(bloque + 1) * ancho] = rng.normal(size=ancho)
    return (v / np.linalg.norm(v)).tolist()


class RankingServiceEntidadesPorChunkTests(TestCase):
    """
    Regresión para el fix de score_entidades: antes se comparaba cada
    artículo contra las entidades de TODO el caso; ahora se compara
    solo contra las entidades del chunk específico que hizo relevante
    a ese artículo (ver RankingService._entidades_por_chunk).

    Sin este fix, un artículo podía recibir score_entidades > 0 por una
    entidad mencionada en una parte del caso totalmente distinta a la
    que realmente lo hizo relevante semánticamente.
    """

    @classmethod
    def setUpTestData(cls):
        rol = Rol.objects.create(nombre="Abogado test ranking")
        cls.usuario = Usuario.objects.create_user(usuario="ranking.test", password="Segura#123", rol=rol)
        cls.cliente = Cliente.objects.create(nombres="Cliente", apellidos="Test")
        cls.rama = RamaDerecho.objects.create(nombre="Rama test ranking")
        jerarquia = Jerarquia.objects.create(nivel=50, nombre="Jerarquía test ranking")
        cls.norma = Norma.objects.create(nombre="Norma test ranking", jerarquia=jerarquia)

        cls.ent_menor = EntidadJuridica.objects.create(nombre="Menor de edad")
        cls.ent_victima = EntidadJuridica.objects.create(nombre="Víctima")
        cls.ent_propietario = EntidadJuridica.objects.create(nombre="Propietario")

        cls.v_a = _vector_bloque(0, seed=1)  # tema "robo"
        cls.v_b = _vector_bloque(1, seed=2)  # tema "violencia familiar"

        cls.articulo_robo = Articulo.objects.create(
            numero_articulo="TEST-A", titulo="Art. TEST-A - ROBO",
            contenido="El que se apoderare de bien mueble ajeno mediante fuerza.",
            norma=cls.norma, rama=cls.rama,
        )
        EmbeddingArticulo.objects.create(articulo=cls.articulo_robo, vector=cls.v_a)
        # A propósito vinculado con "Menor de edad" aunque su contenido real
        # es sobre robo: así se puede detectar si el score de entidades se
        # "presta" indebidamente de otro chunk del mismo caso.
        ArticuloEntidad.objects.create(articulo=cls.articulo_robo, entidad=cls.ent_menor)
        ArticuloEntidad.objects.create(articulo=cls.articulo_robo, entidad=cls.ent_propietario)

        cls.articulo_violencia = Articulo.objects.create(
            numero_articulo="TEST-B", titulo="Art. TEST-B - VIOLENCIA FAMILIAR",
            contenido="El que ejerciere violencia contra una menor de edad en el ámbito familiar.",
            norma=cls.norma, rama=cls.rama,
        )
        EmbeddingArticulo.objects.create(articulo=cls.articulo_violencia, vector=cls.v_b)
        ArticuloEntidad.objects.create(articulo=cls.articulo_violencia, entidad=cls.ent_menor)
        ArticuloEntidad.objects.create(articulo=cls.articulo_violencia, entidad=cls.ent_victima)

    def _crear_caso_con_chunks(self, codigo, chunks_def):
        """chunks_def: lista de (contenido, vector, entidades_detectadas)."""
        caso = Caso.objects.create(
            codigo=codigo, titulo=codigo, descripcion="",
            usuario=self.usuario, cliente=self.cliente, rama_detectada=self.rama,
        )
        for orden, (contenido, vector, entidades) in enumerate(chunks_def, start=1):
            chunk = ChunkCaso.objects.create(caso=caso, contenido=contenido, orden=orden, tipo="texto")
            EmbeddingChunk.objects.create(chunk=chunk, vector=vector)
            for nombre in entidades:
                EntidadDetectadaCaso.objects.create(chunk=chunk, valor_detectado=nombre, score=1.0)
        return caso

    def test_caso_corto_sin_entidades_no_falla_y_score_entidades_es_cero(self):
        """Caso 1: descripción corta tipo 'intento robo', sin entidades."""
        caso = self._crear_caso_con_chunks(
            "CASO-CORTO-SIN-ENTIDADES",
            chunks_def=[("intento robo", self.v_a, [])],
        )
        resultados = RankingService.calcular_ranking(caso)

        self.assertTrue(len(resultados) >= 1)
        resultado_a = next(r for r in resultados if r.articulo_id == self.articulo_robo.id)
        self.assertEqual(float(resultado_a.score_entidades), 0.0)

    def test_entidad_de_otro_chunk_no_contamina_un_articulo_no_relacionado(self):
        """
        Caso 2: el chunk de "robo" no debe recibir crédito por la entidad
        "Menor de edad" que solo aparece en el chunk de "violencia
        familiar", aunque el artículo de robo esté vinculado a esa
        entidad por otro motivo.
        """
        caso = self._crear_caso_con_chunks(
            "CASO-LARGO-DOS-TEMAS",
            chunks_def=[
                ("El imputado sustrajo bienes de la vivienda mediante fuerza sobre las cosas.",
                 self.v_a, []),
                ("Se denuncia que agredió a su hija, una menor de edad, en el ámbito familiar.",
                 self.v_b, ["Menor de edad"]),
            ],
        )
        resultados = RankingService.calcular_ranking(caso)
        resultados_por_articulo = {r.articulo_id: r for r in resultados}

        resultado_robo = resultados_por_articulo[self.articulo_robo.id]
        resultado_violencia = resultados_por_articulo[self.articulo_violencia.id]

        # El fix: el artículo de robo NO se beneficia de la entidad
        # detectada en el chunk de violencia familiar.
        self.assertEqual(float(resultado_robo.score_entidades), 0.0)
        # El artículo de violencia familiar sí recibe el crédito completo,
        # porque la entidad viene de SU propio chunk.
        self.assertEqual(float(resultado_violencia.score_entidades), 1.0)

    def test_articulo_recibe_credito_completo_cuando_coincide_con_su_propio_chunk(self):
        caso = self._crear_caso_con_chunks(
            "CASO-COINCIDENCIA-DIRECTA",
            chunks_def=[
                ("Se denuncia que agredió a su hija, una menor de edad, en el ámbito familiar. La víctima presenta lesiones.",
                 self.v_b, ["Menor de edad", "Víctima"]),
            ],
        )
        resultados = RankingService.calcular_ranking(caso)
        resultado = next(r for r in resultados if r.articulo_id == self.articulo_violencia.id)
        self.assertEqual(float(resultado.score_entidades), 1.0)
